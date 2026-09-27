"""Gerador de XMLs de NF-e sinteticas para testes e treinamento."""

import pathlib
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from nfe_analytics.fiscal import calc_dv_chave, random_cnpj

NS_NFE = "http://www.portalfiscal.inf.br/nfe"
NS_PREFIX = "nfe"

EMITENTES = [
    {"cnpj": "11444777000080", "xNome": "Metalurgica Sul Ltda", "UF": "RS", "cUF": "43", "aliq": 17.0},
    {"cnpj": "22555888000080", "xNome": "Comercial Serra Gaucha SA", "UF": "RS", "cUF": "43", "aliq": 17.0},
    {"cnpj": "33666999000080", "xNome": "Industria Planalto Ltda", "UF": "SC", "cUF": "42", "aliq": 17.0},
    {"cnpj": "44777000000097", "xNome": "Distribuidora Vale do Aco SA", "UF": "MG", "cUF": "31", "aliq": 18.0},
    {"cnpj": "55888111000097", "xNome": "Autopecas Paulista Ltda", "UF": "SP", "cUF": "35", "aliq": 18.0},
    {"cnpj": "66999222000097", "xNome": "Ferragens Curitiba SA", "UF": "PR", "cUF": "41", "aliq": 19.5},
]

# Aliquotas de ICMS por UF. Valores simplificados para fins de geracao sintetica.
ALIQ_UF = {"RS": 17.0, "SC": 17.0, "MG": 18.0, "SP": 18.0, "PR": 19.5}

PRODUTOS = [
    {"cProd": "P001", "xProd": "Parafuso sextavado M8", "NCM": "73181500", "uCom": "UN", "min": 0.50, "max": 2.00},
    {"cProd": "P002", "xProd": "Chapa de aco 2mm", "NCM": "72091700", "uCom": "KG", "min": 4.00, "max": 8.00},
    {"cProd": "P003", "xProd": "Cabo eletrico 2.5mm", "NCM": "85444900", "uCom": "M", "min": 1.50, "max": 3.50},
    {"cProd": "P004", "xProd": "Rolamento esferas", "NCM": "84821000", "uCom": "UN", "min": 15.00, "max": 60.00},
    {"cProd": "P005", "xProd": "Tinta industrial", "NCM": "32082000", "uCom": "KG", "min": 20.00, "max": 45.00},
    {"cProd": "P006", "xProd": "Tubo PVC 100mm", "NCM": "39172300", "uCom": "M", "min": 8.00, "max": 18.00},
]


def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Adiciona subelemento com texto ao elemento pai."""
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def generate_nfe(rng: random.Random, numero: int, defect: str | None = None) -> str:
    """Gera o XML completo de uma NF-e sintetica.

    Args:
        rng: Gerador aleatorio controlado.
        numero: Numero sequencial da nota (nNF).
        defect: None ou um dos tres tipos de defeito: "chave_invalida",
                "total_incorreto", "xml_truncado".
    """
    emitente = rng.choice(EMITENTES)
    aliq = emitente["aliq"]

    destinatario_cnpj = random_cnpj(rng)
    destinatario_nome = f"Cliente {rng.randint(1, 9999):04d}"
    destinatario_uf = rng.choice(list(ALIQ_UF.keys()))

    tz_brt = timezone(timedelta(hours=-3))
    hoje = datetime.now(tz_brt).date()
    dias_atras = rng.randint(0, 89)
    data_base = hoje - timedelta(days=dias_atras)
    hora = rng.randint(0, 23)
    minuto = rng.randint(0, 59)
    segundo = rng.randint(0, 59)
    dh_emi = datetime(data_base.year, data_base.month, data_base.day, hora, minuto, segundo, tzinfo=tz_brt)
    dh_emi_str = dh_emi.strftime("%Y-%m-%dT%H:%M:%S-03:00")

    c_nf = f"{rng.randint(0, 99999999):08d}"
    aamm = dh_emi.strftime("%y%m")
    c_uf = emitente["cUF"]

    chave_43 = f"{c_uf}{aamm}{emitente['cnpj']}55001{numero:09d}1{c_nf}"
    dv = calc_dv_chave(chave_43)
    chave_44 = f"{chave_43}{dv}"

    n_itens = rng.randint(1, 4)
    itens = []
    for i in range(n_itens):
        prod = rng.choice(PRODUTOS)
        q_com = rng.randint(1, 20)
        v_un_com = round(rng.uniform(prod["min"], prod["max"]), 2)
        v_prod = round(q_com * v_un_com, 2)
        cst = rng.choice(["00", "20", "40"])

        if cst == "00":
            v_bc = v_prod
            v_icms = round(v_bc * aliq / 100, 2)
        elif cst == "20":
            v_bc = round(v_prod * 0.6, 2)  # simplificacao: reducao de base fixa em 60%
            v_icms = round(v_bc * aliq / 100, 2)
        else:  # CST 40: isento
            v_bc = 0.0
            v_icms = 0.0

        v_pis = round(v_prod * 0.0165, 2)  # simplificacao: PIS fixo em 1.65%
        v_cofins = round(v_prod * 0.076, 2)  # simplificacao: COFINS fixo em 7.60%

        itens.append({
            "nItem": str(i + 1),
            "cProd": prod["cProd"],
            "xProd": prod["xProd"],
            "NCM": prod["NCM"],
            "uCom": prod["uCom"],
            "qCom": q_com,
            "vUnCom": v_un_com,
            "vProd": v_prod,
            "CST": cst,
            "vBC": v_bc,
            "pICMS": aliq if cst != "40" else None,
            "vICMS": v_icms,
            "vPIS": v_pis,
            "vCOFINS": v_cofins,
        })

    tot_v_bc = round(sum(it["vBC"] for it in itens), 2)
    tot_v_icms = round(sum(it["vICMS"] for it in itens), 2)
    tot_v_prod = round(sum(it["vProd"] for it in itens), 2)
    tot_v_pis = round(sum(it["vPIS"] for it in itens), 2)
    tot_v_cofins = round(sum(it["vCOFINS"] for it in itens), 2)

    n_prot = f"143{aamm}000000001"

    ET.register_namespace(NS_PREFIX, NS_NFE)
    ET.register_namespace("", "")

    nfe_proc = ET.Element(f"{{{NS_NFE}}}nfeProc", attrib={"versao": "4.00"})
    n_fe = ET.SubElement(nfe_proc, f"{{{NS_NFE}}}NFe")
    inf_nfe = ET.SubElement(n_fe, f"{{{NS_NFE}}}infNFe", attrib={"Id": f"NFe{chave_44}", "versao": "4.00"})

    ide = ET.SubElement(inf_nfe, f"{{{NS_NFE}}}ide")
    _sub(ide, f"{{{NS_NFE}}}cUF", c_uf)
    _sub(ide, f"{{{NS_NFE}}}nNF", f"{numero:09d}")
    _sub(ide, f"{{{NS_NFE}}}serie", "001")
    _sub(ide, f"{{{NS_NFE}}}dhEmi", dh_emi_str)

    emit = ET.SubElement(inf_nfe, f"{{{NS_NFE}}}emit")
    _sub(emit, f"{{{NS_NFE}}}CNPJ", emitente["cnpj"])
    _sub(emit, f"{{{NS_NFE}}}xNome", emitente["xNome"])
    ender_emit = ET.SubElement(emit, f"{{{NS_NFE}}}enderEmit")
    _sub(ender_emit, f"{{{NS_NFE}}}UF", emitente["UF"])

    dest = ET.SubElement(inf_nfe, f"{{{NS_NFE}}}dest")
    _sub(dest, f"{{{NS_NFE}}}CNPJ", destinatario_cnpj)
    _sub(dest, f"{{{NS_NFE}}}xNome", destinatario_nome)
    ender_dest = ET.SubElement(dest, f"{{{NS_NFE}}}enderDest")
    _sub(ender_dest, f"{{{NS_NFE}}}UF", destinatario_uf)

    for item in itens:
        det = ET.SubElement(inf_nfe, f"{{{NS_NFE}}}det", attrib={"nItem": item["nItem"]})
        prod = ET.SubElement(det, f"{{{NS_NFE}}}prod")
        _sub(prod, f"{{{NS_NFE}}}cProd", item["cProd"])
        _sub(prod, f"{{{NS_NFE}}}xProd", item["xProd"])
        _sub(prod, f"{{{NS_NFE}}}NCM", item["NCM"])
        _sub(prod, f"{{{NS_NFE}}}CFOP", "5102")
        _sub(prod, f"{{{NS_NFE}}}uCom", item["uCom"])
        _sub(prod, f"{{{NS_NFE}}}qCom", str(item["qCom"]))
        _sub(prod, f"{{{NS_NFE}}}vUnCom", f"{item['vUnCom']:.2f}")
        _sub(prod, f"{{{NS_NFE}}}vProd", f"{item['vProd']:.2f}")

        imposto = ET.SubElement(det, f"{{{NS_NFE}}}imposto")
        icms = ET.SubElement(imposto, f"{{{NS_NFE}}}ICMS")

        cst = item["CST"]
        icms_tag = f"{{{NS_NFE}}}ICMS{cst}"
        icms_det = ET.SubElement(icms, icms_tag)
        _sub(icms_det, f"{{{NS_NFE}}}CST", cst)
        if cst != "40":
            _sub(icms_det, f"{{{NS_NFE}}}vBC", f"{item['vBC']:.2f}")
            _sub(icms_det, f"{{{NS_NFE}}}pICMS", f"{item['pICMS']:.2f}")
        _sub(icms_det, f"{{{NS_NFE}}}vICMS", f"{item['vICMS']:.2f}")

        pis = ET.SubElement(imposto, f"{{{NS_NFE}}}PIS")
        pis_aliq = ET.SubElement(pis, f"{{{NS_NFE}}}PISAliq")
        _sub(pis_aliq, f"{{{NS_NFE}}}vBC", f"{item['vProd']:.2f}")
        _sub(pis_aliq, f"{{{NS_NFE}}}pPIS", "1.65")
        _sub(pis_aliq, f"{{{NS_NFE}}}vPIS", f"{item['vPIS']:.2f}")

        cofins = ET.SubElement(imposto, f"{{{NS_NFE}}}COFINS")
        cofins_aliq = ET.SubElement(cofins, f"{{{NS_NFE}}}COFINSAliq")
        _sub(cofins_aliq, f"{{{NS_NFE}}}vBC", f"{item['vProd']:.2f}")
        _sub(cofins_aliq, f"{{{NS_NFE}}}pCOFINS", "7.60")
        _sub(cofins_aliq, f"{{{NS_NFE}}}vCOFINS", f"{item['vCOFINS']:.2f}")

    total = ET.SubElement(inf_nfe, f"{{{NS_NFE}}}total")
    icms_tot = ET.SubElement(total, f"{{{NS_NFE}}}ICMSTot")
    _sub(icms_tot, f"{{{NS_NFE}}}vBC", f"{tot_v_bc:.2f}")
    _sub(icms_tot, f"{{{NS_NFE}}}vICMS", f"{tot_v_icms:.2f}")
    _sub(icms_tot, f"{{{NS_NFE}}}vProd", f"{tot_v_prod:.2f}")
    _sub(icms_tot, f"{{{NS_NFE}}}vNF", f"{tot_v_prod:.2f}")  # simplificacao: vNF = vProd
    _sub(icms_tot, f"{{{NS_NFE}}}vPIS", f"{tot_v_pis:.2f}")
    _sub(icms_tot, f"{{{NS_NFE}}}vCOFINS", f"{tot_v_cofins:.2f}")

    prot_nfe = ET.SubElement(nfe_proc, f"{{{NS_NFE}}}protNFe", attrib={"versao": "4.00"})
    inf_prot = ET.SubElement(prot_nfe, f"{{{NS_NFE}}}infProt")
    _sub(inf_prot, f"{{{NS_NFE}}}chNFe", chave_44)
    _sub(inf_prot, f"{{{NS_NFE}}}dhRecbto", dh_emi_str)
    _sub(inf_prot, f"{{{NS_NFE}}}nProt", n_prot)
    _sub(inf_prot, f"{{{NS_NFE}}}cStat", "100")
    _sub(inf_prot, f"{{{NS_NFE}}}xMotivo", "Autorizado o uso da NF-e")

    xml_str = ET.tostring(nfe_proc, encoding="unicode")
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    if defect == "chave_invalida":
        dv_errado = (dv + 1) % 10
        chave_44_errada = f"{chave_43}{dv_errado}"
        xml_str = xml_str.replace(chave_44, chave_44_errada)
    elif defect == "total_incorreto":
        tot_corrompido = tot_v_prod + 10.0
        partes = xml_str.split(f"<{NS_PREFIX}:total>", 1)
        partes[1] = partes[1].replace(f"<{NS_PREFIX}:vProd>{tot_v_prod:.2f}</{NS_PREFIX}:vProd>",
                                      f"<{NS_PREFIX}:vProd>{tot_corrompido:.2f}</{NS_PREFIX}:vProd>", 1)
        xml_str = f"<{NS_PREFIX}:total>".join(partes)
    elif defect == "xml_truncado":
        tam = len(xml_str)
        ponto = int(rng.uniform(tam * 0.50, tam * 0.90))
        xml_str = xml_str[:ponto]

    return xml_str


def generate_batch(
    n: int, seed: int, out_dir: pathlib.Path, defect_rate: float = 0.0
) -> list[str]:
    """Gera n arquivos XML de NF-e sinteticas em out_dir.

    Args:
        n: Quantidade de notas a gerar.
        seed: Semente para o gerador aleatorio.
        out_dir: Diretorio de saida (criado se necessario).
        defect_rate: Fracao de documentos com defeito (0.0 a 1.0).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    nomes: list[str] = []

    for i in range(n):
        numero = i + 1
        usa_defect = rng.random() < defect_rate
        defect = None
        if usa_defect:
            defect = rng.choice(["chave_invalida", "total_incorreto", "xml_truncado"])

        xml_str = generate_nfe(rng, numero, defect=defect)
        nome = f"nfe_{i + 1:04d}.xml"
        (out_dir / nome).write_text(xml_str, encoding="utf-8")
        nomes.append(nome)

    return nomes
