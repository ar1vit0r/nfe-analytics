"""Testes do gerador de XMLs de NF-e sinteticas."""

import hashlib
import random
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from nfe_analytics.fiscal import valid_chave, valid_cnpj
from nfe_analytics.generator import EMITENTES, generate_batch, generate_nfe

NS_NFE = "http://www.portalfiscal.inf.br/nfe"


def _parse_xml(xml_str: str) -> ET.Element:
    """Parse de XML com namespace NFe."""
    ET.register_namespace("nfe", NS_NFE)
    return ET.fromstring(xml_str)


def _extrair_chave(root: ET.Element) -> str:
    """Extrai a chave de acesso (44 digitos) do XML parseado."""
    inf_nfe = root.find(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe")
    return inf_nfe.attrib["Id"].removeprefix("NFe")


def _extrair_cnpj_emitente(root: ET.Element) -> str:
    """Extrai o CNPJ do emitente do XML parseado."""
    emit = root.find(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe/{{{NS_NFE}}}emit")
    return emit.find(f"{{{NS_NFE}}}CNPJ").text


def _soma_vprod_itens(root: ET.Element) -> float:
    """Soma vProd de todos os itens det do XML."""
    inf_nfe = root.find(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe")
    total = 0.0
    for det in inf_nfe.findall(f"{{{NS_NFE}}}det"):
        v_prod = det.find(f"{{{NS_NFE}}}prod/{{{NS_NFE}}}vProd")
        total += float(v_prod.text)
    return round(total, 2)


def _vprod_total(root: ET.Element) -> float:
    """Obtem vProd do total/ICMSTot do XML."""
    total_el = root.find(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe/{{{NS_NFE}}}total/{{{NS_NFE}}}ICMSTot/{{{NS_NFE}}}vProd")
    return float(total_el.text)


def _arquivo_defeituoso(xml_str: str) -> bool:
    """Verifica se um XML tem defeito: falha no parse, chave invalida, ou total inconsistente."""
    try:
        root = _parse_xml(xml_str)
    except ET.ParseError:
        return True  # xml_truncado

    chave = _extrair_chave(root)
    if not valid_chave(chave):
        return True  # chave_invalida

    itens_sum = _soma_vprod_itens(root)
    total_prod = _vprod_total(root)
    if abs(itens_sum - total_prod) > 0.01:
        return True  # total_incorreto

    return False


def _arquivo_ok(xml_str: str) -> bool:
    """Verifica se um XML NAO tem defeito."""
    return not _arquivo_defeituoso(xml_str)


class TestGenerateNfe:
    def test_formato_e_tag_raiz(self):
        xml_str = generate_nfe(random.Random(1), numero=1)
        assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "nfeProc" in xml_str

    def test_chave_valida(self):
        xml_str = generate_nfe(random.Random(1), numero=1)
        root = _parse_xml(xml_str)
        chave = _extrair_chave(root)
        assert valid_chave(chave), f"Chave invalida: {chave}"

    def test_cnpj_emitente_valido(self):
        xml_str = generate_nfe(random.Random(1), numero=1)
        root = _parse_xml(xml_str)
        cnpj = _extrair_cnpj_emitente(root)
        assert valid_cnpj(cnpj), f"CNPJ invalido: {cnpj}"
        cnpjs_tabela = {e["cnpj"] for e in EMITENTES}
        assert cnpj in cnpjs_tabela, f"CNPJ nao esta na tabela: {cnpj}"

    def test_total_consistente_com_itens(self):
        xml_str = generate_nfe(random.Random(1), numero=1)
        root = _parse_xml(xml_str)
        soma_itens = _soma_vprod_itens(root)
        total_vprod = _vprod_total(root)
        assert abs(soma_itens - total_vprod) < 0.01, (
            f"Soma itens={soma_itens}, total={total_vprod}"
        )


class TestGenerateBatch:
    def test_determinismo(self, tmp_path: Path):
        nomes_a = generate_batch(5, seed=42, out_dir=tmp_path / "a")
        nomes_b = generate_batch(5, seed=42, out_dir=tmp_path / "b")
        assert nomes_a == nomes_b
        for nome in nomes_a:
            hash_a = hashlib.sha256((tmp_path / "a" / nome).read_bytes()).hexdigest()
            hash_b = hashlib.sha256((tmp_path / "b" / nome).read_bytes()).hexdigest()
            assert hash_a == hash_b, f"Arquivo {nome} difere entre as chamadas"

    def test_batch_grande(self, tmp_path: Path):
        nomes = generate_batch(200, seed=42, out_dir=tmp_path / "batch")
        assert len(nomes) == 200
        assert len(set(nomes)) == 200, "Nomes devem ser todos distintos"

    def test_defect_rate_total(self, tmp_path: Path):
        """Com defect_rate=1.0, todos os arquivos devem ter defeito."""
        nomes = generate_batch(20, seed=42, out_dir=tmp_path / "defect100", defect_rate=1.0)
        assert len(nomes) == 20
        for nome in nomes:
            xml_str = (tmp_path / "defect100" / nome).read_text(encoding="utf-8")
            assert _arquivo_defeituoso(xml_str), f"{nome} deveria ter defeito"

    def test_defect_rate_zero(self, tmp_path: Path):
        """Com defect_rate=0.0, nenhum arquivo deve ter defeito."""
        nomes = generate_batch(20, seed=42, out_dir=tmp_path / "nodefect", defect_rate=0.0)
        assert len(nomes) == 20
        for nome in nomes:
            xml_str = (tmp_path / "nodefect" / nome).read_text(encoding="utf-8")
            assert _arquivo_ok(xml_str), f"{nome} nao deveria ter defeito"

    def test_tres_tipos_defeito_varias_seeds(self, tmp_path: Path):
        """Ao longo de varias seeds, os 3 tipos de defeito devem aparecer."""
        tipos_encontrados: set[str] = set()
        for s in range(1, 31):
            nomes = generate_batch(20, seed=s, out_dir=tmp_path / f"seed_{s}", defect_rate=1.0)
            for nome in nomes:
                xml_str = (tmp_path / f"seed_{s}" / nome).read_text(encoding="utf-8")
                try:
                    root = _parse_xml(xml_str)
                except ET.ParseError:
                    tipos_encontrados.add("xml_truncado")
                    continue
                chave = _extrair_chave(root)
                if not valid_chave(chave):
                    tipos_encontrados.add("chave_invalida")
                    continue
                itens_sum = _soma_vprod_itens(root)
                total_prod = _vprod_total(root)
                if abs(itens_sum - total_prod) > 0.01:
                    tipos_encontrados.add("total_incorreto")
        esperados = {"chave_invalida", "total_incorreto", "xml_truncado"}
        assert tipos_encontrados == esperados, f"Esperado {esperados}, encontrado {tipos_encontrados}"

    def test_total_incorreto_afeta_apenas_total(self):
        """Nota com 1 item: o defect total_incorreto deve alterar o total, nao o item."""
        seed = 4  # seed que gera nota com 1 det
        xml_ok = generate_nfe(random.Random(seed), 1, defect=None)
        xml_def = generate_nfe(random.Random(seed), 1, defect="total_incorreto")

        root_ok = _parse_xml(xml_ok)
        root_def = _parse_xml(xml_def)

        itens_ok = root_ok.findall(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe/{{{NS_NFE}}}det")
        itens_def = root_def.findall(f"{{{NS_NFE}}}NFe/{{{NS_NFE}}}infNFe/{{{NS_NFE}}}det")
        assert len(itens_ok) == 1
        assert len(itens_def) == 1

        v_prod_item_ok = float(itens_ok[0].find(f"{{{NS_NFE}}}prod/{{{NS_NFE}}}vProd").text)
        v_prod_item_def = float(itens_def[0].find(f"{{{NS_NFE}}}prod/{{{NS_NFE}}}vProd").text)
        assert v_prod_item_ok == v_prod_item_def, "vProd do item nao deve mudar"

        assert abs(_vprod_total(root_def) - (_vprod_total(root_ok) + 10.0)) < 0.01, "vProd do total deve ter +10.00"
