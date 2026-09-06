from sqlalchemy.orm import Session

from app.models.loja import Loja
from app.utils.security import hash_senha, verificar_senha


class EmailJaCadastradoError(Exception):
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Já existe uma loja cadastrada com o email {email}")


class CredenciaisInvalidasError(Exception):
    def __init__(self):
        super().__init__("Email ou senha inválidos")


def cadastrar_loja(db: Session, *, nome: str, email: str, senha: str) -> Loja:
    if db.query(Loja).filter(Loja.email == email).first() is not None:
        raise EmailJaCadastradoError(email)

    loja = Loja(nome=nome, email=email, senha_hash=hash_senha(senha))
    db.add(loja)
    db.commit()
    db.refresh(loja)
    return loja


def autenticar_loja(db: Session, *, email: str, senha: str) -> Loja:
    loja = db.query(Loja).filter(Loja.email == email).first()

    if loja is None or not verificar_senha(senha, loja.senha_hash):
        raise CredenciaisInvalidasError()

    if not loja.ativo:
        raise CredenciaisInvalidasError()

    return loja