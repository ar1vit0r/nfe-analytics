"""Parser de XMLs de NF-e para dataclasses tipadas."""

import pathlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

NS_NFE = "http://www.portalfiscal.inf.br/nfe"


class NfeParseError(Exception):
    """Erro de leitura do XML. A mensagem vira motivo de rejeicao na Fase 4."""


@dataclass(frozen=True)
class Item:
    n_item: int
    c_prod: str
    x_prod: str
    ncm: str
    cfop: str
    u_com: str
    q_com: Decimal
    v_un_com: Decimal
    v_prod: Decimal
    icms_cst: str
    icms_v_bc: Decimal | None
    icms_aliq: Decimal | None
    icms_valor: Decimal
    pis_valor: Decimal
    cofins_valor: Decimal


@dataclass(frozen=True)
class Document:
    chave: str
    ch_nfe_prot: str
    numero: int
    serie: int
    dh_emi: datetime
    emit_cnpj: str
    emit_nome: str
    emit_uf: str
    dest_cnpj: str
    dest_nome: str
    dest_uf: str
    v_bc: Decimal
    v_icms: Decimal
    v_prod: Decimal
    v_nf: Decimal
    v_pis: Decimal
    v_cofins: Decimal
    itens: tuple[Item, ...]


def _tag(name: str) -> str:
    return f"{{{NS_NFE}}}{name}"


def _text(el: ET.Element, path: str) -> str:
    child = el.find(_tag(path))
    if child is None or child.text is None:
        raise NfeParseError(f"elemento ausente: {path}")
    return child.text


_DECIMAL_RE = re.compile(r"\d{1,20}(\.\d{1,10})?", re.ASCII)


def _decimal(el: ET.Element, path: str) -> Decimal:
    txt = _text(el, path)
    if _DECIMAL_RE.fullmatch(txt) is None:
        raise NfeParseError(f"valor invalido em {path}")
    return Decimal(txt)


def _int(el: ET.Element, path: str) -> int:
    txt = _text(el, path)
    if not txt.isascii() or not txt.isdigit() or len(txt) > 9:
        raise NfeParseError(f"valor invalido em {path}")
    return int(txt)


def _parse_icms(imposto: ET.Element) -> tuple[str, Decimal | None, Decimal | None, Decimal]:
    icms = imposto.find(_tag("ICMS"))
    if icms is None:
        raise NfeParseError("elemento ausente: ICMS")

    suportados = {"ICMS00", "ICMS20", "ICMS40"}
    children = list(icms)
    if len(children) != 1:
        raise NfeParseError("grupo ICMS invalido: esperado exatamente um filho")
    child = children[0]
    local_name = child.tag.removeprefix(f"{{{NS_NFE}}}")

    if local_name not in suportados:
        raise NfeParseError(f"grupo ICMS nao suportado: {local_name}")

    cst = _text(child, "CST")
    expected_cst = local_name.removeprefix("ICMS")
    if cst != expected_cst:
        raise NfeParseError(f"CST incompativel com o grupo {local_name}: {cst}")
    v_icms = _decimal(child, "vICMS")

    if local_name in ("ICMS00", "ICMS20"):
        v_bc = _decimal(child, "vBC")
        aliq = _decimal(child, "pICMS")
    else:
        v_bc = None
        aliq = None

    return cst, v_bc, aliq, v_icms


def _parse_item(det: ET.Element) -> Item:
    n_item_str = det.attrib.get("nItem")
    if n_item_str is None:
        raise NfeParseError("elemento ausente: nItem")
    if not n_item_str.isascii() or not n_item_str.isdigit() or len(n_item_str) > 9:
        raise NfeParseError("valor invalido em nItem")
    n_item = int(n_item_str)
    prod = det.find(_tag("prod"))
    if prod is None:
        raise NfeParseError("elemento ausente: prod")

    imposto = det.find(_tag("imposto"))
    if imposto is None:
        raise NfeParseError("elemento ausente: imposto")

    pis_el = imposto.find(_tag("PIS"))
    if pis_el is None:
        raise NfeParseError("elemento ausente: PIS")
    pis_aliq = pis_el.find(_tag("PISAliq"))
    if pis_aliq is None:
        raise NfeParseError("elemento ausente: PISAliq")
    pis_valor = _decimal(pis_aliq, "vPIS")

    cofins_el = imposto.find(_tag("COFINS"))
    if cofins_el is None:
        raise NfeParseError("elemento ausente: COFINS")
    cofins_aliq = cofins_el.find(_tag("COFINSAliq"))
    if cofins_aliq is None:
        raise NfeParseError("elemento ausente: COFINSAliq")
    cofins_valor = _decimal(cofins_aliq, "vCOFINS")

    cst, v_bc, aliq, v_icms = _parse_icms(imposto)

    return Item(
        n_item=n_item,
        c_prod=_text(prod, "cProd"),
        x_prod=_text(prod, "xProd"),
        ncm=_text(prod, "NCM"),
        cfop=_text(prod, "CFOP"),
        u_com=_text(prod, "uCom"),
        q_com=_decimal(prod, "qCom"),
        v_un_com=_decimal(prod, "vUnCom"),
        v_prod=_decimal(prod, "vProd"),
        icms_cst=cst,
        icms_v_bc=v_bc,
        icms_aliq=aliq,
        icms_valor=v_icms,
        pis_valor=pis_valor,
        cofins_valor=cofins_valor,
    )


def parse_file(path: pathlib.Path) -> Document:
    """Le um XML de NF-e e retorna um Document tipado."""
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        raise NfeParseError(f"XML malformado: {e}") from None
    except LookupError as e:
        raise NfeParseError(f"XML malformado: {e}") from None

    root = tree.getroot()
    if root.tag != _tag("nfeProc"):
        tag_raiz = root.tag.removeprefix(f"{{{NS_NFE}}}")
        raise NfeParseError(f"raiz inesperada: {tag_raiz}")

    nfe = root.find(_tag("NFe"))
    if nfe is None:
        raise NfeParseError("elemento ausente: NFe")

    inf_nfe = nfe.find(_tag("infNFe"))
    if inf_nfe is None:
        raise NfeParseError("elemento ausente: infNFe")

    chave_com_prefixo = inf_nfe.attrib.get("Id")
    if chave_com_prefixo is None:
        raise NfeParseError("elemento ausente: Id")
    if not chave_com_prefixo.startswith("NFe"):
        raise NfeParseError("valor invalido em Id")
    chave = chave_com_prefixo[3:]

    prot_nfe = root.find(_tag("protNFe"))
    if prot_nfe is None:
        raise NfeParseError("elemento ausente: protNFe")
    inf_prot = prot_nfe.find(_tag("infProt"))
    if inf_prot is None:
        raise NfeParseError("elemento ausente: infProt")
    ch_nfe_prot = _text(inf_prot, "chNFe")

    ide = inf_nfe.find(_tag("ide"))
    if ide is None:
        raise NfeParseError("elemento ausente: ide")
    numero = _int(ide, "nNF")
    serie = _int(ide, "serie")
    dh_emi_str = _text(ide, "dhEmi")
    try:
        dh_emi = datetime.fromisoformat(dh_emi_str)
    except ValueError:
        raise NfeParseError("valor invalido em dhEmi") from None
    if dh_emi.tzinfo is None:
        raise NfeParseError("valor invalido em dhEmi")

    emit = inf_nfe.find(_tag("emit"))
    if emit is None:
        raise NfeParseError("elemento ausente: emit")
    emit_cnpj = _text(emit, "CNPJ")
    emit_nome = _text(emit, "xNome")
    ender_emit = emit.find(_tag("enderEmit"))
    if ender_emit is None:
        raise NfeParseError("elemento ausente: enderEmit")
    emit_uf = _text(ender_emit, "UF")

    dest = inf_nfe.find(_tag("dest"))
    if dest is None:
        raise NfeParseError("elemento ausente: dest")
    dest_cnpj = _text(dest, "CNPJ")
    dest_nome = _text(dest, "xNome")
    ender_dest = dest.find(_tag("enderDest"))
    if ender_dest is None:
        raise NfeParseError("elemento ausente: enderDest")
    dest_uf = _text(ender_dest, "UF")

    itens: list[Item] = []
    for det in inf_nfe.findall(_tag("det")):
        itens.append(_parse_item(det))

    if not itens:
        raise NfeParseError("elemento ausente: det")

    total_el = inf_nfe.find(_tag("total"))
    if total_el is None:
        raise NfeParseError("elemento ausente: total")
    icms_tot = total_el.find(_tag("ICMSTot"))
    if icms_tot is None:
        raise NfeParseError("elemento ausente: ICMSTot")

    v_bc = _decimal(icms_tot, "vBC")
    v_icms = _decimal(icms_tot, "vICMS")
    v_prod = _decimal(icms_tot, "vProd")
    v_nf = _decimal(icms_tot, "vNF")
    v_pis = _decimal(icms_tot, "vPIS")
    v_cofins = _decimal(icms_tot, "vCOFINS")

    return Document(
        chave=chave,
        ch_nfe_prot=ch_nfe_prot,
        numero=numero,
        serie=serie,
        dh_emi=dh_emi,
        emit_cnpj=emit_cnpj,
        emit_nome=emit_nome,
        emit_uf=emit_uf,
        dest_cnpj=dest_cnpj,
        dest_nome=dest_nome,
        dest_uf=dest_uf,
        v_bc=v_bc,
        v_icms=v_icms,
        v_prod=v_prod,
        v_nf=v_nf,
        v_pis=v_pis,
        v_cofins=v_cofins,
        itens=tuple(itens),
    )
