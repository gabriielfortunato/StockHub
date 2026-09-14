"""
Dependencies do FastAPI relacionadas a autenticação e plano.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.utils.planos import loja_bloqueada
from app.utils.security import decodificar_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_loja_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Loja:
    """Exige login válido. Não verifica o estado do plano."""
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        loja_id = decodificar_token(token)
    except JWTError:
        raise credenciais_invalidas

    loja = db.query(Loja).filter(Loja.id == loja_id).first()
    if loja is None or not loja.ativo:
        raise credenciais_invalidas

    return loja


def get_loja_ativa(loja_atual: Loja = Depends(get_loja_atual)) -> Loja:
    """
    Exige login válido E que o plano não esteja vencido.

    Use esta dependency (em vez de get_loja_atual) em qualquer rota
    de uso normal do sistema (produtos, categorias, movimentações).
    A rota de pagamento/renovação continua usando get_loja_atual puro,
    para que uma loja bloqueada ainda consiga pagar e se desbloquear.
    """
    if loja_bloqueada(loja_atual):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Seu plano Plus venceu. Renove o pagamento para continuar usando o Stokfy.",
        )
    return loja_atual