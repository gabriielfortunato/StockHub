"""
Funções de segurança: hash de senha e geração/validação de JWT.

A SECRET_KEY vem de uma variável de ambiente em produção (definida
no Render). Localmente, se a variável não existir, usamos um valor
de reserva só para desenvolvimento — nunca use esse valor padrão
em produção de verdade.
"""

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("SECRET_KEY", "chave-apenas-para-desenvolvimento-local")
ALGORITHM = "HS256"
TOKEN_EXPIRA_MINUTOS = 60 * 24  # 24 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha, senha_hash)


def criar_token_acesso(loja_id: int) -> str:
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRA_MINUTOS)
    payload = {"sub": str(loja_id), "exp": expira_em}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> int:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return int(payload["sub"])
