import requests
from fastapi import APIRouter, HTTPException, status
from app.utils.planos import PRECO_PLUS_CENTAVOS

router = APIRouter(prefix="/assinatura")

INFINITE_TAG = "fortunato_dev"
INFINITEPAY_URL = "https://api.checkout.infinitepay.io/links"

# Sua URL de Webhook hospedada no Render
WEBHOOK_URL = "https://stokfy.onrender.com/webhooks/infinitepay"


@router.post("/upgrade")
def upgrade_assinatura():
    headers = {
        "Content-Type": "application/json"
    }

    # Payload atualizado enviando a webhook_url diretamente para a InfinitePay
    payload = {
        "handle": INFINITE_TAG,
        "items": [
            {
                "quantity": 1,
                "price": PRECO_PLUS_CENTAVOS,  # 2990 (R$ 29,90)
                "description": "Assinatura Plano Plus - Stokfy"
            }
        ],
        "webhook_url": WEBHOOK_URL
    }

    try:
        response = requests.post(INFINITEPAY_URL, json=payload, headers=headers)

        print("Status InfinitePay:", response.status_code)
        print("Resposta InfinitePay:", response.text)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro retornado pela InfinitePay ({response.status_code}): {response.text}"
            )

    except requests.exceptions.RequestException as err:
        print("Erro de comunicação HTTP:", str(err))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao se conectar com a InfinitePay: {str(err)}"
        )