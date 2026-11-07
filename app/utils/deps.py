"""
Dependencies do FastAPI relacionadas a autenticação e plano.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.models.funcionario import Funcionario
from app.utils.planos import loja_bloqueada
from app.utils.security import ALGORITHM, SECRET_KEY, decodificar_token

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

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        loja_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credenciais_invalidas

    loja = db.query(Loja).filter(Loja.id == loja_id).first()
    if loja is None or not loja.ativo:
        raise credenciais_invalidas

    if payload.get("tipo") == "funcionario":
        funcionario = db.query(Funcionario).filter(
            Funcionario.id == payload.get("funcionario_id"),
            Funcionario.loja_id == loja.id,
            Funcionario.ativo.is_(True),
        ).first()
        if funcionario is None:
            raise credenciais_invalidas
        if not funcionario.pode_visualizar:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seu acesso não permite visualizar o estoque.")
        payload["pode_editar"] = bool(funcionario.pode_editar)

    return loja


def get_loja_ativa(loja_atual: Loja = Depends(get_loja_atual), token: str = Depends(oauth2_scheme)) -> Loja:
    """
    Exige login válido E que o plano não esteja vencido.

    Use esta dependency (em vez de get_loja_atual) em qualquer rota
    de uso normal do sistema (produtos, categorias, movimentações).
    A rota de pagamento/renovação continua usando get_loja_atual puro,
    para que uma loja bloqueada ainda consiga pagar e se desbloquear.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    if payload.get("tipo") == "funcionario" and not payload.get("pode_editar", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seu perfil permite apenas visualizar o estoque.")
    if loja_bloqueada(loja_atual):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Seu plano Plus venceu. Renove o pagamento para continuar usando o Stokfy.",
        )
    return loja_atual