import uuid
from datetime import datetime

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.models.pagamento_processado import PagamentoProcessado
from app.utils.deps import get_loja_atual
from app.utils.planos import PRECO_PLUS_CENTAVOS

router = APIRouter(prefix="/assinatura")

INFINITE_TAG = "fortunato_dev"
INFINITEPAY_URL = "https://api.checkout.infinitepay.io/links"
WEBHOOK_URL = "https://stokfy.onrender.com/webhooks/infinitepay"
REDIRECT_URL = "https://stokfy.onrender.com/painel"


@router.post("/upgrade")
def upgrade_assinatura(
    loja: Loja = Depends(get_loja_atual),
    db: Session = Depends(get_db),
):
    # Cada link fica vinculado a um pedido interno e a uma única loja.
    order_nsu = f"stokfy-{uuid.uuid4().hex}"
    pedido = PagamentoProcessado(
        order_nsu=order_nsu,
        valor_centavos=PRECO_PLUS_CENTAVOS,
        loja_id=loja.id,
    )
    db.add(pedido)
    db.commit()

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
        db.delete(pedido)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível gerar o pagamento agora. Tente novamente mais tarde.",
        )
    except requests.exceptions.RequestException:
        db.delete(pedido)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha de comunicação com o serviço de pagamento. Tente novamente mais tarde.",
        )
