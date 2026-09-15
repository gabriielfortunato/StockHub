from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

# Importa a conexão do banco de dados e os modelos do seu projeto
from app.utils.deps import get_db
from app.models import Loja  # Ajuste a importação do modelo Loja se estiver em outro caminho

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/infinitepay")
async def receber_webhook_infinitepay(request: Request, db: Session = Depends(get_db)):
    """
    Recebe a notificação de pagamento confirmado da InfinitePay
    e altera o plano da loja para 'plus' estendendo o acesso por 30 dias.
    """
    try:
        data = await request.json()

        # Exibe o JSON recebido no terminal para fins de log
        print("Webhook recebido da InfinitePay:", data)

        # Identifica o status do pagamento e o identificador do cliente/loja
        status_pagamento = data.get("status") or data.get("event")
        email_cliente = data.get("customer", {}).get("email") or data.get("email")

        # Verifica se o pagamento foi concluído com sucesso
        if status_pagamento in ["approved", "paid", "payment.approved"]:
            if email_cliente:
                loja = db.query(Loja).filter(Loja.email == email_cliente).first()

                if loja:
                    # Atualiza o plano da loja e adiciona 30 dias de expiração
                    loja.plano = "plus"
                    loja.plano_expira_em = datetime.utcnow() + timedelta(days=30)

                    db.add(loja)
                    db.commit()
                    db.refresh(loja)

                    print(f"Plano Plus ativado com sucesso para a loja: {loja.email}")
                    return {"status": "sucesso", "mensagem": "Plano atualizado para Plus com sucesso."}

                print(f"Webhook recebido, mas nenhuma loja encontrada com o email: {email_cliente}")
                return {"status": "alerta", "mensagem": "Loja não encontrada."}

        return {"status": "ignorado", "mensagem": "Status de pagamento não exige atualização de plano."}

    except Exception as err:
        print("Erro ao processar Webhook da InfinitePay:", str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no processamento do webhook: {str(err)}"
        )