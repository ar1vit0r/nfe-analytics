"""Testes do parser de XMLs de NF-e."""

import random
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from nfe_analytics.parser import NfeParseError, parse_file
from nfe_analytics.generator import EMITENTES, generate_batch, generate_nfe

NS_NFE = "http://www.portalfiscal.inf.br/nfe"


def _write_xml(tmp_path: Path, xml_str: str, name: str = "nota.xml") -> Path:
    p = tmp_path / name
    p.write_text(xml_str, encoding="utf-8")
    return p


class TestNotaValida:
    def test_chave_44_digitos_igual_ao_id(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        path = _write_xml(tmp_path, xml_str)
        doc = parse_file(path)
        assert len(doc.chave) == 44
        assert doc.chave.isdigit()

        root = ET.fromstring(xml_str)
        inf_nfe = root.find(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe")
        id_xml = inf_nfe.attrib["Id"].removeprefix("NFe")
        assert doc.chave == id_xml

    def test_emit_cnpj_em_tabela(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        doc = parse_file(_write_xml(tmp_path, xml_str))
        cnpjs_tabela = {e["cnpj"] for e in EMITENTES}
        assert doc.emit_cnpj in cnpjs_tabela

    def test_nitem_ate_n_em_ordem(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        doc = parse_file(_write_xml(tmp_path, xml_str))
        n = len(doc.itens)
        assert [it.n_item for it in doc.itens] == list(range(1, n + 1))

    def test_valores_monetarios_decimal(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        doc = parse_file(_write_xml(tmp_path, xml_str))
        assert isinstance(doc.v_bc, Decimal)
        assert isinstance(doc.v_icms, Decimal)
        assert isinstance(doc.v_prod, Decimal)
        assert isinstance(doc.v_nf, Decimal)
        assert isinstance(doc.v_pis, Decimal)
        assert isinstance(doc.v_cofins, Decimal)
        for it in doc.itens:
            assert isinstance(it.q_com, Decimal)
            assert isinstance(it.v_un_com, Decimal)
            assert isinstance(it.v_prod, Decimal)
            assert isinstance(it.icms_valor, Decimal)
            assert isinstance(it.pis_valor, Decimal)
            assert isinstance(it.cofins_valor, Decimal)

    def test_dh_emi_com_timezone(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        doc = parse_file(_write_xml(tmp_path, xml_str))
        assert doc.dh_emi.tzinfo is not None


class TestBatchParsing:
    def test_seeds_0_49_todas_parseiam(self, tmp_path: Path):
        cst_encontrado: set[str] = set()
        for seed in range(50):
            xml_str = generate_nfe(random.Random(seed), numero=1)
            path = _write_xml(tmp_path, xml_str, f"nota_{seed}.xml")
            doc = parse_file(path)
            for it in doc.itens:
                cst_encontrado.add(it.icms_cst)
                if it.icms_cst == "40":
                    assert it.icms_v_bc is None
                    assert it.icms_aliq is None
                else:
                    assert it.icms_v_bc is not None
                    assert it.icms_aliq is not None
        assert cst_encontrado == {"00", "20", "40"}


class TestErros:
    def test_xml_truncado(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        path = _write_xml(tmp_path, xml_str)
        xml_truncado = xml_str[: len(xml_str) // 2]
        path_truncado = tmp_path / "truncado.xml"
        path_truncado.write_text(xml_truncado, encoding="utf-8")
        with pytest.raises(NfeParseError, match="XML malformado"):
            parse_file(path_truncado)

    def test_grupo_icms_nao_suportado(self, tmp_path: Path):
        xml_str = None
        for seed in range(100):
            xml_str = generate_nfe(random.Random(seed), numero=1)
            if "ICMS00>" in xml_str:
                break
        assert xml_str is not None and "ICMS00>" in xml_str, "nenhuma seed com o grupo procurado"
        xml_mod = xml_str.replace("ICMS00>", "ICMS10>")
        assert "ICMS10>" in xml_mod
        path = tmp_path / "icms10.xml"
        path.write_text(xml_mod, encoding="utf-8")
        with pytest.raises(NfeParseError, match="ICMS"):
            parse_file(path)

    def test_elemento_ausente(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = xml_str.replace("ICMSTot>", "Xtot>")
        path = tmp_path / "ausente.xml"
        path.write_text(xml_mod, encoding="utf-8")
        with pytest.raises(NfeParseError, match="elemento ausente"):
            parse_file(path)

    def test_raiz_errada(self, tmp_path: Path):
        path = tmp_path / "errada.xml"
        path.write_text("<foo/>", encoding="utf-8")
        with pytest.raises(NfeParseError, match="raiz inesperada"):
            parse_file(path)

    def test_nitem_ausente(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = xml_str.replace(' nItem="1"', "", 1)
        path = tmp_path / "sem_nitem.xml"
        path.write_text(xml_mod, encoding="utf-8")
        with pytest.raises(NfeParseError, match="elemento ausente: nItem"):
            parse_file(path)

    def test_nitem_nao_inteiro(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = xml_str.replace('nItem="1"', 'nItem="x"')
        path = tmp_path / "nitem_x.xml"
        path.write_text(xml_mod, encoding="utf-8")
        with pytest.raises(NfeParseError, match="valor invalido em nItem"):
            parse_file(path)

    def test_vicms_nan(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:vICMS>[^<]+</nfe:vICMS>", "<nfe:vICMS>NaN</nfe:vICMS>", xml_str, count=1)
        path = tmp_path / "nan.xml"
        path.write_text(xml_mod, encoding="utf-8")
        with pytest.raises(NfeParseError, match="valor invalido em vICMS"):
            parse_file(path)

    def test_vicms_infinity(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:vICMS>[^<]+</nfe:vICMS>", "<nfe:vICMS>Infinity</nfe:vICMS>", xml_str, count=1)
        path = tmp_path / "inf.xml"
        path.write_text(xml_mod, encoding="utf-8")
        with pytest.raises(NfeParseError, match="valor invalido em vICMS"):
            parse_file(path)

    def test_dhemi_sem_fuso(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = xml_str.replace("-03:00</nfe:dhEmi>", "</nfe:dhEmi>")
        path = tmp_path / "sem_tz.xml"
        path.write_text(xml_mod, encoding="utf-8")
        with pytest.raises(NfeParseError, match="valor invalido em dhEmi"):
            parse_file(path)

    def test_vprod_exponencial(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:vProd>[^<]+</nfe:vProd>", "<nfe:vProd>1E+1000000</nfe:vProd>", xml_str, count=1)
        path = _write_xml(tmp_path, xml_mod, "exp.xml")
        with pytest.raises(NfeParseError, match="valor invalido em vProd"):
            parse_file(path)

    def test_vprod_negativo(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:vProd>[^<]+</nfe:vProd>", "<nfe:vProd>-5.00</nfe:vProd>", xml_str, count=1)
        path = _write_xml(tmp_path, xml_mod, "neg.xml")
        with pytest.raises(NfeParseError, match="valor invalido em vProd"):
            parse_file(path)

    def test_nnf_com_underscore(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = xml_str.replace("</nfe:nNF>", "1_0</nfe:nNF>")
        path = _write_xml(tmp_path, xml_mod, "underscore.xml")
        with pytest.raises(NfeParseError, match="valor invalido em nNF"):
            parse_file(path)

    def test_nitem_mais(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = xml_str.replace('nItem="1"', 'nItem="+1"')
        path = _write_xml(tmp_path, xml_mod, "nitem_mais.xml")
        with pytest.raises(NfeParseError, match="valor invalido em nItem"):
            parse_file(path)

    def test_id_sem_prefixo_nfe(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        root = ET.fromstring(xml_str)
        inf_nfe = root.find(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe")
        id_val = inf_nfe.attrib["Id"]
        xml_mod = xml_str.replace(f'Id="{id_val}"', f'Id="{id_val[3:]}"')
        path = _write_xml(tmp_path, xml_mod, "id_semprefixo.xml")
        with pytest.raises(NfeParseError, match="valor invalido em Id"):
            parse_file(path)

    def test_id_ausente(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        root = ET.fromstring(xml_str)
        inf_nfe = root.find(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe")
        id_val = inf_nfe.attrib["Id"]
        xml_mod = xml_str.replace(f' Id="{id_val}"', "")
        path = _write_xml(tmp_path, xml_mod, "id_ausente.xml")
        with pytest.raises(NfeParseError, match="elemento ausente: Id"):
            parse_file(path)

    def test_cst_incompativel_grupo(self, tmp_path: Path):
        xml_str = None
        for seed in range(50):
            xml_str = generate_nfe(random.Random(seed), numero=1)
            if "ICMS00>" in xml_str and "ICMS40>" in xml_str:
                break
        assert xml_str is not None and "ICMS00>" in xml_str, "nenhuma seed com o grupo procurado"
        root = ET.fromstring(xml_str)
        xml_mod = None
        for icms_sub in root.iter(f"{{{NS_NFE}}}ICMS"):
            for child in icms_sub:
                local = child.tag.removeprefix(f"{{{NS_NFE}}}")
                if local == "ICMS00":
                    cst_el = child.find(f"{{{NS_NFE}}}CST")
                    if cst_el is not None:
                        xml_mod = xml_str.replace(
                            f">{cst_el.text}</nfe:CST>",
                            ">40</nfe:CST>",
                            1,
                        )
                        break
            else:
                continue
            break
        assert xml_mod is not None
        path = _write_xml(tmp_path, xml_mod, "cst_errado.xml")
        with pytest.raises(NfeParseError, match="CST incompativel"):
            parse_file(path)

    def test_nota_sem_det(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:det[^>]*>.*?</nfe:det>", "", xml_str, flags=re.S)
        path = _write_xml(tmp_path, xml_mod, "sem_det.xml")
        with pytest.raises(NfeParseError, match="elemento ausente: det"):
            parse_file(path)

    def test_nnf_5000_digitos(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:nNF>[^<]+</nfe:nNF>", "<nfe:nNF>" + "9" * 5000 + "</nfe:nNF>", xml_str)
        path = _write_xml(tmp_path, xml_mod, "nnf_grande.xml")
        with pytest.raises(NfeParseError, match="valor invalido em nNF"):
            parse_file(path)

    def test_nitem_5000_digitos(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r'nItem="1"', 'nItem="' + "9" * 5000 + '"', xml_str)
        path = _write_xml(tmp_path, xml_mod, "nitem_grande.xml")
        with pytest.raises(NfeParseError, match="valor invalido em nItem"):
            parse_file(path)

    def test_nnf_10_digitos(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:nNF>[^<]+</nfe:nNF>", "<nfe:nNF>1234567890</nfe:nNF>", xml_str)
        path = _write_xml(tmp_path, xml_mod, "nnf_10.xml")
        with pytest.raises(NfeParseError, match="valor invalido em nNF"):
            parse_file(path)

    def test_nnf_9_digitos(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:nNF>[^<]+</nfe:nNF>", "<nfe:nNF>999999999</nfe:nNF>", xml_str)
        path = _write_xml(tmp_path, xml_mod, "nnf_9.xml")
        doc = parse_file(path)
        assert doc.numero == 999999999

    def test_vprod_menos_zero(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:vProd>[^<]+</nfe:vProd>", "<nfe:vProd>-0</nfe:vProd>", xml_str, count=1)
        path = _write_xml(tmp_path, xml_mod, "vprod_menos0.xml")
        with pytest.raises(NfeParseError, match="valor invalido em vProd"):
            parse_file(path)

    def test_vprod_menos_zero_ponto_zero_zero(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(r"<nfe:vProd>[^<]+</nfe:vProd>", "<nfe:vProd>-0.00</nfe:vProd>", xml_str, count=1)
        path = _write_xml(tmp_path, xml_mod, "vprod_menos000.xml")
        with pytest.raises(NfeParseError, match="valor invalido em vProd"):
            parse_file(path)

    def test_xml_encoding_foo(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        xml_mod = re.sub(
            r'<\?xml version="1\.0" encoding="[^"]+"\?>',
            '<?xml version="1.0" encoding="foo"?>',
            xml_str,
        )
        path = _write_xml(tmp_path, xml_mod, "enc_foo.xml")
        with pytest.raises(NfeParseError, match="XML malformado"):
            parse_file(path)

    def test_qcom_invalidos(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        for bad in ("1e3", "+5", ".5", "5.", "1E+2"):
            xml_mod = re.sub(
                r"<nfe:qCom>[^<]+</nfe:qCom>",
                f"<nfe:qCom>{bad}</nfe:qCom>",
                xml_str,
                count=1,
            )
            path = _write_xml(tmp_path, xml_mod, f"qcom_{bad}.xml")
            with pytest.raises(NfeParseError, match="valor invalido em qCom"):
                parse_file(path)

    def test_qcom_validos(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        for val in ("12.5", "7"):
            xml_mod = re.sub(
                r"<nfe:qCom>[^<]+</nfe:qCom>",
                f"<nfe:qCom>{val}</nfe:qCom>",
                xml_str,
                count=1,
            )
            path = _write_xml(tmp_path, xml_mod, f"qcom_{val}.xml")
            doc = parse_file(path)
            assert doc.itens[0].q_com == Decimal(val)

    def test_vprod_21_digitos(self, tmp_path: Path):
        xml_str = generate_nfe(random.Random(1), numero=1)
        big = "9" * 21
        xml_mod = re.sub(
            r"<nfe:vProd>[^<]+</nfe:vProd>",
            f"<nfe:vProd>{big}</nfe:vProd>",
            xml_str,
            count=1,
        )
        path = _write_xml(tmp_path, xml_mod, "vprod_21.xml")
        with pytest.raises(NfeParseError, match="valor invalido em vProd"):
            parse_file(path)
