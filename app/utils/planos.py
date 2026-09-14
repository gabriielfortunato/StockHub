"""
Limites de uso por plano e lógica de bloqueio por vencimento.
"""

from datetime import datetime

LIMITES_PLANO_GRATUITO = {
    "produtos": 10,
    "categorias": 1,
}

PLANO_PLUS = "plus"
PLANO_GRATUITO = "gratuito"

PRECO_PLUS_CENTAVOS = 2990  # R$ 29,90


def loja_bloqueada(loja) -> bool:
    """
    Retorna True se a loja já foi Plus mas o pagamento venceu.

    Uma loja que nunca assinou (plano="gratuito" desde o início) NÃO
    é considerada bloqueada — ela só tem os limites do plano gratuito.
    O bloqueio total é exclusivo de quem foi Plus e não renovou.
    """
    if loja.plano != PLANO_PLUS:
        return False

    if loja.plano_expira_em is None:
        return False

    return loja.plano_expira_em < datetime.utcnow()