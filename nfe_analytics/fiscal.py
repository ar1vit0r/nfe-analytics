import random


def calc_dv_chave(chave43: str) -> int:
    """Calcula o DV de uma chave de acesso de 43 dígitos (módulo 11, pesos 2-9)."""
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    total = 0
    for i, digito in enumerate(reversed(chave43)):
        total += int(digito) * pesos[i % 8]
    resto = total % 11
    return 0 if resto < 2 else 11 - resto


def valid_chave(chave: str) -> bool:
    """Valida chave de acesso de 44 dígitos numéricos."""
    if not chave or not chave.isascii() or not chave.isdigit() or len(chave) != 44:
        return False
    return int(chave[43]) == calc_dv_chave(chave[:43])


def calc_cnpj_dv(cnpj12: str) -> str:
    """Calcula os 2 dígitos verificadores de um CNPJ de 12 dígitos."""
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total1 = sum(int(cnpj12[i]) * pesos1[i] for i in range(12))
    resto1 = total1 % 11
    dv1 = 0 if resto1 < 2 else 11 - resto1

    cnpj13 = cnpj12 + str(dv1)
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total2 = sum(int(cnpj13[i]) * pesos2[i] for i in range(13))
    resto2 = total2 % 11
    dv2 = 0 if resto2 < 2 else 11 - resto2

    return f"{dv1}{dv2}"


def valid_cnpj(cnpj: str) -> bool:
    """Valida CNPJ de 14 dígitos numéricos. Rejeita dígitos todos iguais."""
    if not cnpj or not cnpj.isascii() or not cnpj.isdigit() or len(cnpj) != 14:
        return False
    if len(set(cnpj)) == 1:
        return False
    return cnpj[12:] == calc_cnpj_dv(cnpj[:12])


def random_cnpj(rng: random.Random) -> str:
    """Gera um CNPJ válido aleatório usando o RNG fornecido."""
    digits = "".join(str(rng.randint(0, 9)) for _ in range(12))
    return digits + calc_cnpj_dv(digits)
