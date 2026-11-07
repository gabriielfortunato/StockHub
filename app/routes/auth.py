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
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
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
from app.utils.planos import loja_bloqueada, loja_tem_plus
from app.utils.security import ALGORITHM, SECRET_KEY, criar_token_acesso, hash_senha, verificar_senha

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
TEMPO_TOKEN_RECUPERACAO_MINUTOS = 30


class LojaCadastro(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class SolicitarRecuperacao(BaseModel):
    email: EmailStr


class ExcluirConta(BaseModel):
    senha: str


class AdminContaAtualizar(BaseModel):
    ativo: bool | None = None
    plano: str | None = None
    plano_expira_em: Optional[datetime] = None


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
    teste_gratis_ate: Optional[datetime] = None
    teste_gratis: bool = False
    teste_gratis_disponivel: bool = False
    teste_gratis_iniciado_em: Optional[datetime] = None
    plano_vencido: bool = False
    regularizacao_pendente: bool = False

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


@router.delete("/conta")
def excluir_conta(
    dados: ExcluirConta,
    loja: Loja = Depends(get_loja_atual),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Exclui permanentemente a conta autenticada após confirmar a senha."""
    if jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("tipo") == "funcionario":
        raise HTTPException(status_code=403, detail="Somente o responsável pela loja pode excluir a conta.")
    if not verificar_senha(dados.senha, loja.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha incorreta. A conta não foi excluída.",
        )

    try:
        db.delete(loja)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível excluir a conta agora. Tente novamente mais tarde.",
        )

    return {"mensagem": "Conta excluída com sucesso."}


@router.get("/me", response_model=LojaMeResposta)
def obter_loja_logada(loja: Loja = Depends(get_loja_atual)):
    return {
        "id": loja.id,
        "nome": loja.nome,
        "email": loja.email,
        "plano": "plus" if loja_tem_plus(loja) else "gratuito",
        "plano_expira_em": loja.plano_expira_em,
        "teste_gratis_ate": loja.teste_gratis_ate,
        "teste_gratis": bool(loja.teste_gratis_ate and loja.teste_gratis_ate >= datetime.utcnow()),
        "teste_gratis_disponivel": loja.teste_gratis_iniciado_em is None and not loja_tem_plus(loja),
        "teste_gratis_iniciado_em": loja.teste_gratis_iniciado_em,
        "plano_vencido": loja_bloqueada(loja),
        "regularizacao_pendente": (
            not loja_tem_plus(loja)
            and loja.produtos is not None
            and sum(1 for produto in loja.produtos if produto.ativo) > 10
        ),
    }


@router.post("/iniciar-teste")
def iniciar_teste_gratis(
    loja: Loja = Depends(get_loja_atual),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Inicia o teste Plus somente após solicitação explícita do titular da loja."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("tipo") == "funcionario":
        raise HTTPException(status_code=403, detail="Somente o responsável pela loja pode iniciar o teste grátis.")

    conta = db.query(Loja).filter(Loja.id == loja.id).with_for_update().first()
    if conta is None or not conta.ativo:
        raise HTTPException(status_code=404, detail="Conta não encontrada ou inativa.")
    if conta.teste_gratis_iniciado_em is not None:
        raise HTTPException(status_code=409, detail="O teste grátis desta conta já foi utilizado.")
    if loja_tem_plus(conta):
        raise HTTPException(status_code=409, detail="Sua conta já possui acesso ao Plus.")

    agora = datetime.utcnow()
    conta.plano = "plus"
    conta.plano_expira_em = agora + timedelta(days=7)
    conta.teste_gratis_ate = agora + timedelta(days=7)
    conta.teste_gratis_iniciado_em = agora
    db.commit()
    db.refresh(conta)
    return {
        "mensagem": "Teste grátis iniciado. Você tem 7 dias de acesso ao Stokfy Plus.",
        "teste_gratis": True,
        "teste_gratis_ate": conta.teste_gratis_ate,
    }


# Endpoints exclusivos do painel administrativo e presença dos usuários.
EMAIL_ADMINISTRADOR = os.getenv("ADMIN_EMAIL", "gfortunato713@gmail.com").strip().lower()


def _exigir_administrador(loja: Loja, token: str) -> None:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("tipo") == "funcionario" or (loja.email or "").strip().lower() != EMAIL_ADMINISTRADOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao administrador.")


@router.post("/atividade")
def registrar_atividade(loja: Loja = Depends(get_loja_atual), db: Session = Depends(get_db)):
    """Registra que a conta está utilizando o Stokfy neste momento."""
    loja.ultima_atividade = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"mensagem": "Atividade registrada."}


@router.delete("/admin/contas/{conta_id}")
def excluir_conta_pelo_admin(
    conta_id: int,
    loja_admin: Loja = Depends(get_loja_atual),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Permite somente ao administrador excluir uma conta de terceiro."""
    _exigir_administrador(loja_admin, token)
    if conta_id == loja_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use a opção de exclusão da tela principal para excluir sua própria conta.",
        )

    conta = db.query(Loja).filter(Loja.id == conta_id).first()
    if conta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada.")

    try:
        db.delete(conta)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível excluir esta conta. Nenhum dado foi removido.",
        )

    return {"mensagem": "Conta e dados associados excluídos com sucesso."}


@router.patch("/admin/contas/{conta_id}")
def atualizar_conta_pelo_admin(
    conta_id: int,
    dados: AdminContaAtualizar,
    loja_admin: Loja = Depends(get_loja_atual),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    _exigir_administrador(loja_admin, token)
    if conta_id == loja_admin.id:
        raise HTTPException(status_code=400, detail="Não é possível bloquear ou alterar o plano da própria conta por aqui.")
    conta = db.query(Loja).filter(Loja.id == conta_id).first()
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    alteracoes = dados.model_dump(exclude_unset=True)
    if "plano" in alteracoes:
        if alteracoes["plano"] not in {"gratuito", "plus"}:
            raise HTTPException(status_code=400, detail="Plano inválido.")
        conta.plano = alteracoes["plano"]
        conta.teste_gratis_ate = None
        if alteracoes["plano"] == "plus" and conta.teste_gratis_iniciado_em is None:
            conta.teste_gratis_iniciado_em = datetime.utcnow()
    if "ativo" in alteracoes:
        conta.ativo = alteracoes["ativo"]
    if "plano_expira_em" in alteracoes:
        conta.plano_expira_em = alteracoes["plano_expira_em"]
    db.commit()
    return {"mensagem": "Conta atualizada.", "ativo": conta.ativo, "plano": conta.plano}

@router.get("/admin/visao-geral")
def obter_visao_geral_admin(
    loja_admin: Loja = Depends(get_loja_atual),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Entrega dados administrativos somente ao e-mail autorizado."""
    _exigir_administrador(loja_admin, token)

    agora = datetime.now(timezone.utc).replace(tzinfo=None)
    limite_atividade = agora - timedelta(minutes=15)
    contas = db.query(Loja).order_by(Loja.criado_em.desc()).all()

    contas_ativas = sum(
        1 for conta in contas
        if conta.ativo and conta.ultima_atividade is not None
        and conta.ultima_atividade >= limite_atividade
    )

    return {
        "administrador_id": loja_admin.id,
        "total_contas": len(contas),
        "contas_ativas": contas_ativas,
        "janela_minutos": 15,
        "contas": [
            {
                "id": conta.id,
                "nome": conta.nome,
                "email": conta.email,
                "criado_em": conta.criado_em.isoformat() if conta.criado_em else None,
                "ultima_atividade": conta.ultima_atividade.isoformat() if conta.ultima_atividade else None,
                "ativo": bool(conta.ativo),
                "plano": conta.plano,
                "plano_expira_em": conta.plano_expira_em.isoformat() if conta.plano_expira_em else None,
                "teste_gratis_ate": conta.teste_gratis_ate.isoformat() if conta.teste_gratis_ate else None,
                "teste_gratis_iniciado_em": conta.teste_gratis_iniciado_em.isoformat() if conta.teste_gratis_iniciado_em else None,
                "online": bool(
                    conta.ativo and conta.ultima_atividade is not None
                    and conta.ultima_atividade >= limite_atividade
                ),
            }
            for conta in contas
        ],
    }
