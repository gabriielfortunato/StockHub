"""
Limites de uso por plano e lógica do teste grátis e vencimento.
"""
from datetime import datetime

LIMITES_PLANO_GRATUITO = {"produtos": 10, "categorias": 1}
PLANO_PLUS = "plus"
PLANO_GRATUITO = "gratuito"
PRECO_PLUS_CENTAVOS = 2990
DIAS_TESTE_GRATIS = 7


def loja_tem_plus(loja) -> bool:
    """Indica se a loja tem acesso efetivo ao Plus neste momento."""
    if loja.plano != PLANO_PLUS:
        return False
    agora = datetime.utcnow()
    if loja.teste_gratis_ate is not None and loja.teste_gratis_ate < agora:
        return False
    if loja.plano_expira_em is not None and loja.plano_expira_em < agora:
        return False
    return True


def loja_bloqueada(loja) -> bool:
    """
    Um teste grátis vencido retorna ao plano gratuito.
    Uma assinatura paga vencida fica bloqueada até a renovação.
    """
    if loja.plano != PLANO_PLUS or loja.plano_expira_em is None:
        return False
    if loja.plano_expira_em >= datetime.utcnow():
        return False
    if loja.teste_gratis_ate is not None:
        return False
    return True
