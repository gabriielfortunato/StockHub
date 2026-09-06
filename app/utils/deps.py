"""
Dependency do FastAPI que extrai a loja logada a partir do token JWT.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.utils.security import decodificar_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_loja_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Loja:
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