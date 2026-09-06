"""
Limites de uso por plano.

Centralizar aqui facilita ajustar os números no futuro (ou até
criar mais planos), sem precisar mexer nas rotas.
"""

LIMITES_PLANO_GRATUITO = {
    "produtos": 10,
    "categorias": 1,
}

PLANO_PLUS = "plus"
PLANO_GRATUITO = "gratuito"