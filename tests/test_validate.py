"""Testes do validador de documentos NF-e."""

import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from nfe_analytics.parser import parse_file
from nfe_analytics.validate import TOLERANCIA, validate
from nfe_analytics.generator import generate_nfe, generate_batch

FIXED_NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def _doc_valido(seed: int, tmp_path: Path):
    xml_str = generate_nfe(random.Random(seed), numero=1)
    path = tmp_path / f"nota_{seed}.xml"
    path.write_text(xml_str, encoding="utf-8")
    return parse_file(path)


def _doc_com_defeito(seed: int, defect: str, tmp_path: Path):
    xml_str = generate_nfe(random.Random(seed), numero=1, defect=defect)
    path = tmp_path / f"nota_{seed}_{defect}.xml"
    path.write_text(xml_str, encoding="utf-8")
    return parse_file(path)


def _codigo_de_erro(erro: str) -> str:
    return erro.split(":")[0]


class TestDocsValidos:
    def test_seeds_0_49_validos(self, tmp_path: Path):
        for seed in range(50):
            doc = _doc_valido(seed, tmp_path)
            erros = validate(doc, now=FIXED_NOW)
            assert erros == [], f"seed={seed} erros inesperados: {erros}"


class TestRegraChaveDv:
    def test_chave_dv(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        dv_original = int(doc.chave[43])
        dv_novo = (dv_original + 1) % 10
        chave_nova = doc.chave[:43] + str(dv_novo)
        doc_mod = replace(doc, chave=chave_nova, ch_nfe_prot=chave_nova)
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "chave_dv" in codigos
        assert "id_diverge_chave" not in codigos


class TestRegraIdDivergeChave:
    def test_id_diverge_chave(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        dv_novo = (int(doc.chave[-1]) + 1) % 10
        doc_mod = replace(doc, ch_nfe_prot=doc.chave[:43] + str(dv_novo))
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "id_diverge_chave" in codigos


class TestRegraCnpj:
    def test_cnpj_emitente(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, emit_cnpj="00000000000000")
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "cnpj_emitente" in codigos

    def test_cnpj_destinatario(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, dest_cnpj="00000000000000")
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "cnpj_destinatario" in codigos


class TestRegraTotal:
    def test_total_vprod(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, v_prod=doc.v_prod + Decimal("10"))
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "total_vprod" in codigos

    def test_total_vnf(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, v_nf=doc.v_nf + Decimal("10"))
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "total_vnf" in codigos

    def test_total_vicms(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, v_icms=doc.v_icms + Decimal("5"))
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "total_vicms" in codigos

    def test_total_vpis(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, v_pis=doc.v_pis + Decimal("5"))
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "total_vpis" in codigos

    def test_total_vcofins(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, v_cofins=doc.v_cofins + Decimal("5"))
        erros = validate(doc_mod, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "total_vcofins" in codigos


class TestRegraDataFutura:
    def test_data_futura(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        now = doc.dh_emi - timedelta(days=1)
        erros = validate(doc, now=now)
        assert "data_futura" in [_codigo_de_erro(e) for e in erros]


class TestRegraNitemSequencia:
    def test_nitem_sequencia_1_3(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        if len(doc.itens) < 2:
            pytest.skip("nota com 1 item nao testa sequencia incompleta")
        itens_mod = list(doc.itens)
        itens_mod[1] = replace(itens_mod[1], n_item=3)
        doc_mod = replace(doc, itens=tuple(itens_mod))
        erros = validate(doc_mod, now=FIXED_NOW)
        assert "nitem_sequencia" in [_codigo_de_erro(e) for e in erros]

    def test_nitem_sequencia_2_3(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        if len(doc.itens) < 2:
            pytest.skip("nota com 1 item nao testa sequencia incompleta")
        itens_mod = list(doc.itens)
        itens_mod[0] = replace(itens_mod[0], n_item=2)
        itens_mod[1] = replace(itens_mod[1], n_item=3)
        doc_mod = replace(doc, itens=tuple(itens_mod))
        erros = validate(doc_mod, now=FIXED_NOW)
        assert "nitem_sequencia" in [_codigo_de_erro(e) for e in erros]

    def test_nitem_sequencia_1_1(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        if len(doc.itens) < 2:
            pytest.skip("nota com 1 item nao testa sequencia duplicada")
        itens_mod = list(doc.itens)
        itens_mod[1] = replace(itens_mod[1], n_item=1)
        doc_mod = replace(doc, itens=tuple(itens_mod))
        erros = validate(doc_mod, now=FIXED_NOW)
        assert "nitem_sequencia" in [_codigo_de_erro(e) for e in erros]

    def test_nitem_sequencia_2_1(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        if len(doc.itens) < 2:
            pytest.skip("nota com 1 item nao testa sequencia fora de ordem")
        itens_mod = list(doc.itens)
        itens_mod[0] = replace(itens_mod[0], n_item=2)
        itens_mod[1] = replace(itens_mod[1], n_item=1)
        doc_mod = replace(doc, itens=tuple(itens_mod))
        erros = validate(doc_mod, now=FIXED_NOW)
        assert "nitem_sequencia" in [_codigo_de_erro(e) for e in erros]

    def test_nitem_sequencia_valida(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        n = len(doc.itens)
        sequencia = [it.n_item for it in doc.itens]
        assert sequencia == list(range(1, n + 1))
        erros = validate(doc, now=FIXED_NOW)
        assert "nitem_sequencia" not in [_codigo_de_erro(e) for e in erros]


class TestTolerancia:
    def test_tolerancia_exata_ok(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, v_prod=doc.v_prod + Decimal("0.01"))
        erros = validate(doc_mod, now=FIXED_NOW)
        assert "total_vprod" not in [_codigo_de_erro(e) for e in erros]

    def test_tolerancia_ultrapassa_erro(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(doc, v_prod=doc.v_prod + Decimal("0.02"))
        erros = validate(doc_mod, now=FIXED_NOW)
        assert "total_vprod" in [_codigo_de_erro(e) for e in erros]


class TestDefeitosPontaAPonta:
    def test_chave_invalida(self, tmp_path: Path):
        doc = _doc_com_defeito(1, "chave_invalida", tmp_path)
        erros = validate(doc, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "chave_dv" in codigos
        assert "id_diverge_chave" not in codigos

    def test_total_incorreto(self, tmp_path: Path):
        doc = _doc_com_defeito(1, "total_incorreto", tmp_path)
        erros = validate(doc, now=FIXED_NOW)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "total_vprod" in codigos

    def test_xml_truncado(self, tmp_path: Path):
        from nfe_analytics.parser import NfeParseError
        xml_str = generate_nfe(random.Random(1), numero=1, defect="xml_truncado")
        path = tmp_path / "truncado.xml"
        path.write_text(xml_str, encoding="utf-8")
        with pytest.raises(NfeParseError):
            parse_file(path)


class TestMultiplosErros:
    def test_dois_erros_simultaneos(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_mod = replace(
            doc,
            emit_cnpj="00000000000000",
            dh_emi=doc.dh_emi + timedelta(days=1),
        )
        erros = validate(doc_mod, now=doc.dh_emi)
        codigos = [_codigo_de_erro(e) for e in erros]
        assert "cnpj_emitente" in codigos
        assert "data_futura" in codigos

    def test_now_none_data_futura(self, tmp_path: Path):
        doc = _doc_valido(1, tmp_path)
        doc_futuro = replace(doc, dh_emi=datetime.now(timezone.utc) + timedelta(days=1))
        erros = validate(doc_futuro)
        assert "data_futura" in [_codigo_de_erro(e) for e in erros]
        erros_original = validate(doc)
        assert "data_futura" not in [_codigo_de_erro(e) for e in erros_original]
