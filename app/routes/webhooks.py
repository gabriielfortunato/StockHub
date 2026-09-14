"""
Webhook recebido da InfinitePay quando um pagamento é confirmado.

Esta rota é pública (a InfinitePay chama ela diretamente, sem token
de loja), então a validação é feita pelo conteúdo do próprio aviso:
o order_nsu precisa bater com o formato que nós mesmos geramos em
pagamento_service.criar_link_pagamento_upgrade().
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.services.pagamento_service import extrair_loja_id_do_order_nsu
from app.utils.planos import PLANO_PLUS, PRECO_PLUS_CENTAVOS

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/infinitepay")
async def receber_webhook_infinitepay(request: Request, db: Session = Depends(get_db)):
    corpo = await request.json()

    order_nsu = corpo.get("order_nsu", "")
    paid_amount = corpo.get("paid_amount", 0)

    loja_id = extrair_loja_id_do_order_nsu(order_nsu)
    if loja_id is None:
        # Não é um pagamento que reconhecemos — ignora silenciosamente.
        return {"status": "ignorado"}

    if paid_amount < PRECO_PLUS_CENTAVOS:
        # Valor pago menor que o esperado — não libera o upgrade.
        return {"status": "valor_insuficiente"}

    loja = db.query(Loja).filter(Loja.id == loja_id).first()
    if loja is None:
        return {"status": "loja_nao_encontrada"}

    loja.plano = PLANO_PLUS
    loja.plano_expira_em = datetime.utcnow() + timedelta(days=30)
    db.add(loja)
    db.commit()

    return {"status": "ok"}