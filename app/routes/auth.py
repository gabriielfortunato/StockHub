"""
Rotas de cadastro e login de loja.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.auth_service import (
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    autenticar_loja,
    cadastrar_loja,
)
from app.utils.security import criar_token_acesso

router = APIRouter(prefix="/auth", tags=["auth"])


class LojaCadastro(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class LojaResposta(BaseModel):
    id: int
    nome: str
    email: str

    class Config:
        from_attributes = True


class TokenResposta(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/cadastro", response_model=LojaResposta, status_code=status.HTTP_201_CREATED)
def cadastro(dados: LojaCadastro, db: Session = Depends(get_db)):
    try:
        loja = cadastrar_loja(db, nome=dados.nome, email=dados.email, senha=dados.senha)
    except EmailJaCadastradoError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    return loja


@router.post("/login", response_model=TokenResposta)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Usa o campo "username" do formulário como email (padrão do
    OAuth2PasswordRequestForm, que é o esperado pelo Swagger/FastAPI).
    """
    try:
        loja = autenticar_loja(db, email=form.username, senha=form.password)
    except CredenciaisInvalidasError as erro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(erro))

    token = criar_token_acesso(loja.id)
    return TokenResposta(access_token=token)