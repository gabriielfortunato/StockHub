"""
Rotas de cadastro, login, recuperação de senha e perfil da loja.
"""

import hashlib
import hmac
import html
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Loja
from app.services.auth_service import (
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    autenticar_loja,
    cadastrar_loja,
)
from app.utils.deps import get_loja_atual
from app.utils.planos import loja_bloqueada
from app.utils.security import ALGORITHM, SECRET_KEY, criar_token_acesso, hash_senha

router = APIRouter(prefix="/auth", tags=["auth"])
TEMPO_TOKEN_RECUPERACAO_MINUTOS = 30


class LojaCadastro(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class SolicitarRecuperacao(BaseModel):
    email: EmailStr


class RedefinirSenha(BaseModel):
    token: str
    senha: str


class LojaResposta(BaseModel):
    id: int
    nome: str
    email: str

    class Config:
        from_attributes = True


class LojaMeResposta(BaseModel):
    id: int
    nome: str
    email: str
    plano: str
    plano_expira_em: Optional[datetime] = None
    plano_vencido: bool = False

    class Config:
        from_attributes = True


class TokenResposta(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _impressao_senha(senha_hash: str) -> str:
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        senha_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _senha_valida(senha: str) -> bool:
    return (
        len(senha) >= 8
        and any(c.isupper() for c in senha)
        and any(c.islower() for c in senha)
        and any(c.isdigit() for c in senha)
    )


def _enviar_email_recuperacao(destinatario: str, nome: str, link: str) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    remetente = os.getenv("EMAIL_FROM")
    if not api_key or not remetente:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A recuperação por e-mail ainda não foi configurada. Tente novamente mais tarde.",
        )

    nome_seguro = html.escape(nome)
    link_seguro = html.escape(link, quote=True)
    try:
        resposta = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from": remetente,
                "to": [destinatario],
                "subject": "Redefinição de senha - Stokfy",
                "html": (
                    f"<p>Olá, {nome_seguro}.</p>"
                    "<p>Recebemos uma solicitação para redefinir a senha da sua conta Stokfy.</p>"
                    f'<p><a href="{link_seguro}">Criar uma nova senha</a></p>'
                    "<p>Este link expira em 30 minutos. Se você não solicitou a alteração, "
                    "ignore este e-mail. Sua senha atual continuará a mesma.</p>"
                ),
            },
            timeout=15,
        )
        resposta.raise_for_status()
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível enviar o e-mail agora. Tente novamente mais tarde.",
        )


@router.post("/cadastro", response_model=LojaResposta, status_code=status.HTTP_201_CREATED)
def cadastro(dados: LojaCadastro, db: Session = Depends(get_db)):
    if not _senha_valida(dados.senha):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha precisa ter pelo menos 8 caracteres, uma letra maiúscula, uma minúscula e um número.",
        )
    try:
        loja = cadastrar_loja(db, nome=dados.nome, email=dados.email, senha=dados.senha)
    except EmailJaCadastradoError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    return loja


@router.post("/login", response_model=TokenResposta)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        loja = autenticar_loja(db, email=form.username, senha=form.password)
    except CredenciaisInvalidasError as erro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(erro))
    token = criar_token_acesso(loja.id)
    return TokenResposta(access_token=token)


@router.post("/solicitar-recuperacao")
def solicitar_recuperacao(dados: SolicitarRecuperacao, request: Request, db: Session = Depends(get_db)):
    # Verifica a configuração antes da consulta para não revelar se um e-mail está cadastrado.
    if not os.getenv("RESEND_API_KEY") or not os.getenv("EMAIL_FROM"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A recuperação por e-mail ainda não foi configurada. Tente novamente mais tarde.",
        )

    loja = db.query(Loja).filter(Loja.email == dados.email).first()
    if loja is None or not loja.ativo:
        return {"mensagem": "Se existir uma conta com esse e-mail, enviaremos um link de recuperação."}

    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(loja.id),
        "purpose": "password_reset",
        "ver": _impressao_senha(loja.senha_hash),
        "exp": agora + timedelta(minutes=TEMPO_TOKEN_RECUPERACAO_MINUTOS),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    base_url = os.getenv("APP_BASE_URL", "https://stokfy.onrender.com").rstrip("/")
    link = f"{base_url}/redefinir-senha?token={token}"
    _enviar_email_recuperacao(loja.email, loja.nome, link)
    return {"mensagem": "Se existir uma conta com esse e-mail, enviaremos um link de recuperação."}


@router.post("/redefinir-senha")
def redefinir_senha(dados: RedefinirSenha, db: Session = Depends(get_db)):
    if not _senha_valida(dados.senha):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha precisa ter pelo menos 8 caracteres, uma letra maiúscula, uma minúscula e um número.",
        )
    try:
        payload = jwt.decode(dados.token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "password_reset":
            raise HTTPException(status_code=400, detail="Link inválido ou expirado.")
        loja_id = int(payload["sub"])
        impressao = payload["ver"]
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Link inválido ou expirado.")

    loja = db.query(Loja).filter(Loja.id == loja_id, Loja.ativo.is_(True)).first()
    if loja is None or not hmac.compare_digest(impressao, _impressao_senha(loja.senha_hash)):
        raise HTTPException(status_code=400, detail="Link inválido, expirado ou já utilizado.")

    loja.senha_hash = hash_senha(dados.senha)
    db.commit()
    return {"mensagem": "Senha redefinida com sucesso. Você já pode entrar com a nova senha."}


@router.get("/me", response_model=LojaMeResposta)
def obter_loja_logada(loja: Loja = Depends(get_loja_atual)):
    return {
        "id": loja.id,
        "nome": loja.nome,
        "email": loja.email,
        "plano": loja.plano,
        "plano_expira_em": loja.plano_expira_em,
        "plano_vencido": loja_bloqueada(loja),
    }
