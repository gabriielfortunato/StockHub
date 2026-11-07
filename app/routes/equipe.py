"""Gerenciamento de funcionários e permissões por loja."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.funcionario import Funcionario
from app.models.loja import Loja as LojaModel
from app.models.loja import Loja
from app.utils.deps import get_loja_atual
from app.utils.security import ALGORITHM, SECRET_KEY, hash_senha, verificar_senha

router = APIRouter(prefix="/equipe", tags=["equipe"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class FuncionarioCriar(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    pode_visualizar: bool = True
    pode_editar: bool = False

class LoginFuncionario(BaseModel):
    email: EmailStr
    senha: str

def _somente_dono(loja: Loja, token: str):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("tipo") == "funcionario":
        raise HTTPException(status_code=403, detail="Somente o responsável pela loja pode gerenciar funcionários.")

@router.get("")
def listar_funcionarios(loja: Loja = Depends(get_loja_atual), db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    _somente_dono(loja, token)
    return [{"id": f.id, "nome": f.nome, "email": f.email, "pode_visualizar": f.pode_visualizar,
             "pode_editar": f.pode_editar, "ativo": f.ativo, "criado_em": f.criado_em.isoformat()}
            for f in db.query(Funcionario).filter(Funcionario.loja_id == loja.id).order_by(Funcionario.nome).all()]

@router.post("", status_code=status.HTTP_201_CREATED)
def criar_funcionario(dados: FuncionarioCriar, loja: Loja = Depends(get_loja_atual),
                      db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    _somente_dono(loja, token)
    if len(dados.senha) < 8 or not any(c.isupper() for c in dados.senha) or not any(c.islower() for c in dados.senha) or not any(c.isdigit() for c in dados.senha):
        raise HTTPException(status_code=400, detail="A senha precisa ter 8 caracteres, maiúscula, minúscula e número.")
    if db.query(Funcionario).filter(Funcionario.email == dados.email).first() or db.query(LojaModel).filter(LojaModel.email == dados.email).first():
        raise HTTPException(status_code=400, detail="Este e-mail já está sendo utilizado.")
    funcionario = Funcionario(nome=dados.nome, email=dados.email, senha_hash=hash_senha(dados.senha),
        pode_visualizar=dados.pode_visualizar, pode_editar=dados.pode_editar, loja_id=loja.id)
    db.add(funcionario); db.commit(); db.refresh(funcionario)
    return {"id": funcionario.id, "nome": funcionario.nome, "email": funcionario.email,
            "pode_visualizar": funcionario.pode_visualizar, "pode_editar": funcionario.pode_editar}

@router.delete("/{funcionario_id}")
def excluir_funcionario(funcionario_id: int, loja: Loja = Depends(get_loja_atual), db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    _somente_dono(loja, token)
    funcionario = db.query(Funcionario).filter(Funcionario.id == funcionario_id, Funcionario.loja_id == loja.id).first()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    db.delete(funcionario); db.commit()
    return {"mensagem": "Acesso do funcionário removido."}

@router.post("/login")
def login_funcionario(dados: LoginFuncionario, db: Session = Depends(get_db)):
    funcionario = db.query(Funcionario).filter(Funcionario.email == dados.email, Funcionario.ativo.is_(True)).first()
    if not funcionario or not funcionario.pode_visualizar or not verificar_senha(dados.senha, funcionario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    agora = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": str(funcionario.loja_id), "tipo": "funcionario", "funcionario_id": funcionario.id,
        "pode_visualizar": bool(funcionario.pode_visualizar), "pode_editar": bool(funcionario.pode_editar),
        "exp": agora + timedelta(hours=8)
    }, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
