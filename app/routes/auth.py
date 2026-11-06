"""
Rotas de cadastro, login, verificação de e-mail e perfil da loja.
"""
import os
from datetime import datetime
from typing import Optional

import requests
from jose import JWTError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
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
from app.utils.security import (
    criar_token_acesso,
    criar_token_verificacao_email,
    decodificar_token_verificacao_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LojaCadastro(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class CadastroResposta(BaseModel):
    id: int
    nome: str
    email: str
    verification_required: bool = False


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


def _verificacao_email_ativada() -> bool:
    return bool(os.getenv("RESEND_API_KEY") and os.getenv("RESEND_FROM_EMAIL"))


def _enviar_email_verificacao(email: str, nome: str, token: str) -> None:
    api_key = os.environ["RESEND_API_KEY"]
    remetente = os.environ["RESEND_FROM_EMAIL"]
    base_url = os.getenv("APP_BASE_URL", "https://stokfy.onrender.com").rstrip("/")
    link = f"{base_url}/auth/verificar-email?token={token}"

    resposta = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": remetente,
            "to": [email],
            "subject": "Confirme seu e-mail - Stokfy",
            "html": (
                f"<p>Olá, {nome}!</p>"
                "<p>Confirme seu endereço de e-mail para ativar sua conta no Stokfy.</p>"
                f'<p><a href="{link}">Confirmar meu e-mail</a></p>'
                "<p>Este link expira em 30 minutos. Se você não criou uma conta, ignore esta mensagem.</p>"
            ),
        },
        timeout=15,
    )
    resposta.raise_for_status()


@router.post("/cadastro", response_model=CadastroResposta, status_code=status.HTTP_201_CREATED)
def cadastro(dados: LojaCadastro, db: Session = Depends(get_db)):
    verificar_email = _verificacao_email_ativada()
    try:
        loja = cadastrar_loja(
            db,
            nome=dados.nome,
            email=dados.email,
            senha=dados.senha,
            ativo=not verificar_email,
        )
    except EmailJaCadastradoError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    if verificar_email:
        token = criar_token_verificacao_email(loja.id)
        try:
            _enviar_email_verificacao(loja.email, loja.nome, token)
        except requests.RequestException:
            db.delete(loja)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível enviar o e-mail de confirmação. Tente novamente mais tarde.",
            )
        return CadastroResposta(
            id=loja.id, nome=loja.nome, email=loja.email, verification_required=True
        )

    return CadastroResposta(
        id=loja.id, nome=loja.nome, email=loja.email, verification_required=False
    )


@router.get("/verificar-email")
def verificar_email(token: str = Query(...), db: Session = Depends(get_db)):
    try:
        loja_id = decodificar_token_verificacao_email(token)
    except (JWTError, ValueError, TypeError):
        return RedirectResponse(url="/login?verificacao=erro", status_code=303)

    loja = db.query(Loja).filter(Loja.id == loja_id).first()
    if loja is None:
        return RedirectResponse(url="/login?verificacao=erro", status_code=303)

    loja.ativo = True
    db.commit()
    return RedirectResponse(url="/login?verificado=1", status_code=303)


@router.post("/login", response_model=TokenResposta)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Usa o campo username do formulário como e-mail."""
    try:
        loja = autenticar_loja(db, email=form.username, senha=form.password)
    except CredenciaisInvalidasError as erro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(erro))

    token = criar_token_acesso(loja.id)
    return TokenResposta(access_token=token)


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
