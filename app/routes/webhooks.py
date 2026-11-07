from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.models import Loja, PagamentoProcessado
from app.utils.deps import get_db
from app.utils.planos import PRECO_PLUS_CENTAVOS
from app.utils.security import ALGORITHM, SECRET_KEY

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

INFINITE_TAG = "fortunato_dev"
PAYMENT_CHECK_URL = "https://api.checkout.infinitepay.io/payment_check"


@router.post("/infinitepay")
def receber_webhook_infinitepay(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Confirma o pagamento diretamente com a InfinitePay antes de liberar o Plus.
    O webhook, sozinho, nunca é considerado prova de pagamento.
    """
    order_nsu = payload.get("order_nsu")
    transaction_nsu = payload.get("transaction_nsu")
    invoice_slug = payload.get("invoice_slug") or payload.get("slug")

    if not order_nsu or not transaction_nsu or not invoice_slug:
        raise HTTPException(status_code=400, detail="Notificação de pagamento incompleta.")

    try:
        pedido = jwt.decode(order_nsu, SECRET_KEY, algorithms=[ALGORITHM])
        if pedido.get("purpose") != "stokfy_plus_payment":
            raise ValueError("Finalidade inválida.")
        loja_id = int(pedido["sub"])
        valor_esperado = int(pedido["amount"])
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Referência de pagamento inválida.")

    if valor_esperado != PRECO_PLUS_CENTAVOS:
        raise HTTPException(status_code=400, detail="Valor do pedido inválido.")

    api_key = os.getenv("INFINITEPAY_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A confirmação segura de pagamentos ainda não foi configurada.",
        )

    try:
        verificacao = requests.post(
            PAYMENT_CHECK_URL,
            json={
                "handle": INFINITE_TAG,
                "order_nsu": order_nsu,
                "transaction_nsu": transaction_nsu,
                "slug": invoice_slug,
            },
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            timeout=10,
        )
        verificacao.raise_for_status()
        resultado = verificacao.json()
    except (requests.RequestException, ValueError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível confirmar o pagamento com segurança. Tente novamente.",
        )

    if not resultado.get("success") or not resultado.get("paid"):
        return {"status": "ignorado", "mensagem": "O pagamento ainda não foi confirmado."}

    try:
        valor_confirmado = int(resultado.get("amount", -1))
    except (TypeError, ValueError):
        valor_confirmado = -1
    if valor_confirmado != valor_esperado:
        raise HTTPException(status_code=400, detail="O valor confirmado não corresponde ao pedido.")

    try:
        pagamento_existente = db.query(PagamentoProcessado).filter(
            PagamentoProcessado.transaction_nsu == str(transaction_nsu)
        ).first()
        if pagamento_existente:
            return {"status": "sucesso", "mensagem": "Este pagamento já foi processado."}

        loja = db.query(Loja).filter(Loja.id == loja_id, Loja.ativo.is_(True)).with_for_update().first()
        if loja is None:
            raise HTTPException(status_code=404, detail="Conta não encontrada.")

        agora = datetime.now(timezone.utc).replace(tzinfo=None)
        inicio = loja.plano_expira_em if loja.plano_expira_em and loja.plano_expira_em > agora else agora
        loja.plano = "plus"
        loja.plano_expira_em = inicio + timedelta(days=30)
        loja.teste_gratis_ate = None
        if loja.teste_gratis_iniciado_em is None:
            loja.teste_gratis_iniciado_em = agora

        db.add(PagamentoProcessado(transaction_nsu=str(transaction_nsu), loja_id=loja.id))
        db.commit()
        return {"status": "sucesso", "mensagem": "Pagamento confirmado e plano atualizado."}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        # A resposta não revela detalhes do banco nem dados pessoais.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível atualizar a assinatura agora.",
        )
