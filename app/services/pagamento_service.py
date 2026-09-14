"""
Integração com a InfinitePay (Checkout Integrado).

Documentação: https://ajuda.infinitepay.io (Checkout Integrado / API)

O fluxo é:
1. A loja clica em "Assinar Plus" -> chamamos criar_link_pagamento(),
   que gera um link de pagamento na InfinitePay.
2. A loja é redirecionada para esse link e paga.
3. A InfinitePay chama nosso webhook (rota /webhooks/infinitepay)
   avisando que o pagamento foi confirmado.
4. No webhook, marcamos a loja como "plus" por mais 30 dias.
"""

import os
import uuid

import requests

from app.utils.planos import PRECO_PLUS_CENTAVOS

INFINITEPAY_HANDLE = os.environ.get("INFINITEPAY_HANDLE", "")
INFINITEPAY_API_URL = "https://api.checkout.infinitepay.io/links"

# URL pública onde o Stokfy está publicado. Usada para montar o
# redirect_url (para onde o cliente volta) e o webhook_url (para onde
# a InfinitePay avisa sobre o pagamento).
URL_BASE_SITE = os.environ.get("URL_BASE_SITE", "http://127.0.0.1:8000")


class PagamentoError(Exception):
    """Levantado quando não foi possível criar o link de pagamento."""


def criar_link_pagamento_upgrade(loja_id: int) -> str:
    """
    Cria um link de pagamento de R$29,90 na InfinitePay para o
    upgrade da loja para o plano Plus.

    O order_nsu carrega o id da loja embutido (ex: "upgrade-loja-7-a1b2c3d4"),
    para que o webhook saiba qual loja atualizar quando o pagamento
    for confirmado.
    """
    if not INFINITEPAY_HANDLE:
        raise PagamentoError("INFINITEPAY_HANDLE não configurado no servidor.")

    identificador_unico = uuid.uuid4().hex[:8]
    order_nsu = f"upgrade-loja-{loja_id}-{identificador_unico}"

    corpo = {
        "handle": INFINITEPAY_HANDLE,
        "redirect_url": f"{URL_BASE_SITE}/painel?upgrade=sucesso",
        "webhook_url": f"{URL_BASE_SITE}/webhooks/infinitepay",
        "order_nsu": order_nsu,
        "items": [
            {
                "quantity": 1,
                "price": PRECO_PLUS_CENTAVOS,
                "description": "Assinatura Stokfy Plus - 1 mes",
            }
        ],
    }

    try:
        resposta = requests.post(INFINITEPAY_API_URL, json=corpo, timeout=10)
        resposta.raise_for_status()
    except requests.RequestException as erro:
        raise PagamentoError(f"Falha ao criar link de pagamento: {erro}") from erro

    dados = resposta.json()
    url_pagamento = dados.get("url")

    if not url_pagamento:
        raise PagamentoError("A InfinitePay não retornou um link de pagamento válido.")

    return url_pagamento


def extrair_loja_id_do_order_nsu(order_nsu: str) -> int | None:
    """
    Extrai o id da loja de um order_nsu no formato "upgrade-loja-{id}-{sufixo}".
    Retorna None se o formato não bater (evita quebrar o webhook com
    dados inesperados).
    """
    partes = order_nsu.split("-")
    if len(partes) < 3 or partes[0] != "upgrade" or partes[1] != "loja":
        return None

    try:
        return int(partes[2])
    except ValueError:
        return None