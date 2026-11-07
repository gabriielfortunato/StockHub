import uuid
from datetime import datetime, timedelta, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt

from app.models.loja import Loja
from app.utils.deps import get_loja_atual
from app.utils.planos import PRECO_PLUS_CENTAVOS
from app.utils.security import ALGORITHM, SECRET_KEY

router = APIRouter(prefix="/assinatura")

INFINITE_TAG = "fortunato_dev"
INFINITEPAY_URL = "https://api.checkout.infinitepay.io/links"
WEBHOOK_URL = "https://stokfy.onrender.com/webhooks/infinitepay"
REDIRECT_URL = "https://stokfy.onrender.com/painel"


@router.post("/upgrade")
def upgrade_assinatura(loja: Loja = Depends(get_loja_atual)):
    # O identificador do pedido é assinado pelo servidor e vincula o checkout à loja.
    agora = datetime.now(timezone.utc)
    order_nsu = jwt.encode(
        {
            "sub": str(loja.id),
            "purpose": "stokfy_plus_payment",
            "jti": uuid.uuid4().hex,
            "amount": PRECO_PLUS_CENTAVOS,
            "exp": agora + timedelta(hours=24),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    payload = {
        "handle": INFINITE_TAG,
        "items": [{
            "quantity": 1,
            "price": PRECO_PLUS_CENTAVOS,
            "description": "Assinatura Plano Plus - Stokfy",
        }],
        "order_nsu": order_nsu,
        "customer": {"email": loja.email},
        "webhook_url": WEBHOOK_URL,
        "redirect_url": REDIRECT_URL,
    }

    try:
        response = requests.post(
            INFINITEPAY_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if response.status_code in (200, 201):
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
