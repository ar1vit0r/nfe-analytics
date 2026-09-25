import random

from nfe_analytics.fiscal import (
    calc_cnpj_dv,
    calc_dv_chave,
    random_cnpj,
    valid_chave,
    valid_cnpj,
)


# --- CNPJ ---


def test_cnpj_valid_known():
    assert valid_cnpj("11222333000181")


def test_cnpj_dv_calc_mao():
    # 12 dígitos: 112223330001, pesos1 5,4,3,2,9,8,7,6,5,4,3,2
    # soma = 1*5+1*4+2*3+2*2+2*9+3*8+3*7+3*6+0*5+0*4+0*3+1*2
    #      = 5+4+6+4+18+24+21+18+0+0+0+2 = 102
    # 102 % 11 = 3, dv1 = 11-3 = 8
    #
    # 13 dígitos: 1122233300018, pesos2 6,5,4,3,2,9,8,7,6,5,4,3,2
    # soma = 1*6+1*5+2*4+2*3+2*2+3*9+3*8+3*7+0*6+0*5+0*4+1*3+8*2
    #      = 6+5+8+6+4+27+24+21+0+0+0+3+16 = 120
    # 120 % 11 = 10, dv2 = 11-10 = 1
    assert calc_cnpj_dv("112223330001") == "81"


def test_cnpj_dv_altered():
    assert not valid_cnpj("11222333000182")


def test_cnpj_all_same():
    for d in "0123456789":
        assert not valid_cnpj(d * 14)


def test_cnpj_wrong_length():
    assert not valid_cnpj("1234567890123")
    assert not valid_cnpj("123456789012345")


def test_cnpj_non_numeric():
    assert not valid_cnpj("1122233300018A")


def test_cnpj_non_ascii():
    assert not valid_cnpj("\u00b2" + "12223330001" + "81")


def test_cnpj_empty():
    assert not valid_cnpj("")


# --- CNPJ: restos 1 e 2 no 1 DV ---


def test_cnpj_dv_resto_1():
    # 200000000001: soma1 = 2*5+1*2 = 12, 12%11=1, dv1=0
    # 13 dígitos: 2000000000010, soma2 = 2*6+1*3+0*2 = 12+3+0 = 15, 15%11=4, dv2=7
    assert calc_cnpj_dv("200000000001") == "07"


def test_cnpj_dv_resto_2():
    # 000000000001: soma1 = 1*2 = 2, 2%11=2, dv1=9
    # 13 dígitos: 0000000000019, soma2 = 1*3+9*2 = 3+18=21, 21%11=10, dv2=1
    assert calc_cnpj_dv("000000000001") == "91"


# --- Chave de acesso ---


def test_chave_valid():
    # corpo de 43 dígitos, DV calculado à mão abaixo
    corpo = "11222333000181" + "0" * 29
    dv = calc_dv_chave(corpo)
    assert valid_chave(corpo + str(dv))


def test_chave_dv_calc_mao():
    # corpo = 11222333000181 + 0*29 (43 dígitos)
    # leitura da direita, pesos (i%8)+2: 2,3,4,5,6,7,8,9,...
    # os 29 zeros à direita (pos 0..28) consomem os pesos, contribuem 0.
    # dígitos não nulos (dir→esq): 1(pos29),8(pos30),1(pos31),3(pos35),
    #   3(pos36),3(pos37),2(pos38),2(pos39),2(pos40),1(pos41),1(pos42)
    # pesos: 7,8,9,5,6,7,8,9,2,3,4
    # soma = 1*7+8*8+1*9+3*5+3*6+3*7+2*8+2*9+2*2+1*3+1*4
    #      = 7+64+9+15+18+21+16+18+4+3+4 = 179
    # 179 % 11 = 3, dv = 11-3 = 8
    corpo = "11222333000181" + "0" * 29
    assert calc_dv_chave(corpo) == 8


def test_chave_wrong_dv():
    corpo = "11222333000181" + "0" * 29
    dv = calc_dv_chave(corpo)
    wrong_dv = (dv + 1) % 10
    assert not valid_chave(corpo + str(wrong_dv))


def test_chave_wrong_length():
    assert not valid_chave("1234567890123456789012345678901234567890123")


def test_chave_non_numeric():
    assert not valid_chave("A" * 44)


def test_chave_non_ascii():
    assert not valid_chave("\u00b2" * 44)


def test_chave_empty():
    assert not valid_chave("")


# --- Chave: restos 0, 1, 2 ---


def test_chave_dv_resto_0():
    # "0"*43: soma=0, 0%11=0 (<2), dv=0
    assert calc_dv_chave("0" * 43) == 0


def test_chave_dv_resto_1():
    # "0"*42+"6": soma=6*2=12 (pos0 peso2), 12%11=1 (<2), dv=0
    assert calc_dv_chave("0" * 42 + "6") == 0


def test_chave_dv_resto_2():
    # "0"*42+"1": soma=1*2=2 (pos0 peso2), 2%11=2 (>=2), dv=11-2=9
    assert calc_dv_chave("0" * 42 + "1") == 9


# --- Propriedades ---


def test_random_cnpj_property():
    for seed in range(1000):
        rng = random.Random(seed)
        cnpj = random_cnpj(rng)
        assert len(cnpj) == 14
        assert cnpj.isdigit()
        assert valid_cnpj(cnpj)


def test_random_cnpj_deterministic():
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    assert random_cnpj(rng1) == random_cnpj(rng2)
