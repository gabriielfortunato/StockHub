from datetime import datetime, timedelta
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models import Loja
from app.utils.deps import get_db

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/infinitepay")
async def receber_webhook_infinitepay(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Recebe a notificação de pagamento confirmado da InfinitePay
    e altera o plano da loja para 'plus' estendendo o acesso por 30 dias.
    """
    try:
        status_pagamento = payload.get("status") or payload.get("event")

        # Captura o e-mail caso ele venha dentro de 'customer' ou diretamente na raiz do JSON
        customer_info = payload.get("customer")
        email_cliente = None
        if isinstance(customer_info, dict):
            email_cliente = customer_info.get("email")
        if not email_cliente:
            email_cliente = payload.get("email")

        if status_pagamento in ["approved", "paid", "payment.approved"]:
            if email_cliente:
                loja = db.query(Loja).filter(Loja.email == email_cliente).first()

                if loja:
                    loja.plano = "plus"
                    loja.plano_expira_em = datetime.utcnow() + timedelta(days=30)
                    loja.teste_gratis_ate = None
                    if loja.teste_gratis_iniciado_em is None:
                        loja.teste_gratis_iniciado_em = datetime.utcnow()

                    db.add(loja)
                    db.commit()
                    db.refresh(loja)

                    return {
                        "status": "sucesso",
                        "mensagem": "Plano atualizado com sucesso.",
                    }

                return {"status": "ignorado", "mensagem": "Evento não associado a uma conta."}

        return {"status": "ignorado", "mensagem": "Status de pagamento não exige atualização de plano."}

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível processar a notificação agora.",
        )