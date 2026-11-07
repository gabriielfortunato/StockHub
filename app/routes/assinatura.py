import requests
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.loja import Loja
from app.utils.deps import get_loja_atual
from app.utils.planos import PRECO_PLUS_CENTAVOS

router = APIRouter(prefix="/assinatura")

INFINITE_TAG = "fortunato_dev"
INFINITEPAY_URL = "https://api.checkout.infinitepay.io/links"

# URLs da sua aplicação no Render (Ajuste se estiver utilizando seu domínio próprio)
WEBHOOK_URL = "https://stokfy.onrender.com/webhooks/infinitepay"
REDIRECT_URL = "https://stokfy.onrender.com/painel"


@router.post("/upgrade")
def upgrade_assinatura(loja: Loja = Depends(get_loja_atual)):
    headers = {
        "Content-Type": "application/json"
    }

    # Envia as URLs de webhook e redirecionamento diretamente para a API do gateway
    payload = {
        "handle": INFINITE_TAG,
        "items": [
            {
                "quantity": 1,
                "price": PRECO_PLUS_CENTAVOS,  # 2990 (R$ 29,90)
                "description": "Assinatura Plano Plus - Stokfy"
            }
        ],
        "webhook_url": WEBHOOK_URL,
        "redirect_url": REDIRECT_URL
    }

    try:
        response = requests.post(INFINITEPAY_URL, json=payload, headers=headers, timeout=15)

        if response.status_code in [200, 201]:
            return response.json()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível gerar o pagamento agora. Tente novamente mais tarde.",
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha de comunicação com o serviço de pagamento. Tente novamente mais tarde.",
        )