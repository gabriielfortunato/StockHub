"""
Rotas de cadastro, login e perfil da loja.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
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
from app.utils.security import criar_token_acesso

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


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


class LojaMeResposta(BaseModel):
    id: int
    nome: str
    email: str
    plano: str
    plano_expira_em: Optional[datetime] = None

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
    Usa o campo "username" do formulário como email.
    """
    try:
        loja = autenticar_loja(db, email=form.username, senha=form.password)
    except CredenciaisInvalidasError as erro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(erro))

    token = criar_token_acesso(loja.id)
    return TokenResposta(access_token=token)


@router.get("/me", response_model=LojaMeResposta)
def obter_loja_logada(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna os dados da loja e o status atual do plano.
    """
    loja = db.query(Loja).first()
    if not loja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma loja cadastrada."
        )
    return loja