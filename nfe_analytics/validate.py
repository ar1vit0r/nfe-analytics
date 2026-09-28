"""Validacao de documentos NF-e parseados."""

from datetime import datetime, timezone
from decimal import Decimal

from nfe_analytics.fiscal import valid_cnpj, valid_chave
from nfe_analytics.parser import Document

# Diferenca maxima aceita entre somas de itens e totais do documento.
# Diferenca exatamente igual a TOLERANCIA NAO e erro; maior que TOLERANCIA e erro.
TOLERANCIA = Decimal("0.01")


def validate(doc: Document, now: datetime | None = None) -> list[str]:
    """Valida um Document e retorna lista de erros (vazia = valido).

    Args:
        doc: Document parseado.
        now: Referencia de tempo para checagem de data futura.
             None usa datetime.now(timezone.utc). Aceita datetime com timezone.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    erros: list[str] = []

    if not valid_chave(doc.chave):
        erros.append("chave_dv: chave com digito verificador invalido")

    if doc.chave != doc.ch_nfe_prot:
        erros.append("id_diverge_chave: chave do infNFe difere de chNFe do protNFe")

    if not valid_cnpj(doc.emit_cnpj):
        erros.append("cnpj_emitente: CNPJ do emitente invalido")

    if not valid_cnpj(doc.dest_cnpj):
        erros.append("cnpj_destinatario: CNPJ do destinatario invalido")

    soma_v_prod = sum(item.v_prod for item in doc.itens)
    if abs(soma_v_prod - doc.v_prod) > TOLERANCIA:
        erros.append("total_vprod: soma de vProd dos itens difere do total")

    # Simplificacao do projeto: sem desconto, frete ou seguro, entao vNF deve ser
    # igual a vProd.
    if abs(doc.v_nf - doc.v_prod) > TOLERANCIA:
        erros.append("total_vnf: vNF difere de vProd")

    soma_v_icms = sum(item.icms_valor for item in doc.itens)
    if abs(soma_v_icms - doc.v_icms) > TOLERANCIA:
        erros.append("total_vicms: soma de icms_valor dos itens difere do total")

    soma_v_pis = sum(item.pis_valor for item in doc.itens)
    if abs(soma_v_pis - doc.v_pis) > TOLERANCIA:
        erros.append("total_vpis: soma de pis_valor dos itens difere do total")

    soma_v_cofins = sum(item.cofins_valor for item in doc.itens)
    if abs(soma_v_cofins - doc.v_cofins) > TOLERANCIA:
        erros.append("total_vcofins: soma de cofins_valor dos itens difere do total")

    if doc.dh_emi > now:
        erros.append("data_futura: data de emissao e posterior a data de referencia")

    sequencia_esperada = list(range(1, len(doc.itens) + 1))
    sequencia_real = [item.n_item for item in doc.itens]
    if sequencia_real != sequencia_esperada:
        erros.append("nitem_sequencia: numeros de item nao sao sequenciais de 1 a N")

    return erros
