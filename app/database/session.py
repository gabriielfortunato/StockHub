"""
Configuração da conexão com o banco de dados.

Localmente (no seu computador), continua usando o SQLite, sem
precisar configurar nada. Quando publicado (Render), a variável de
ambiente DATABASE_URL aponta para o Postgres do Neon, e o código
usa esse banco automaticamente.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./estoque.db")

# O Neon (e outros provedores de Postgres) às vezes fornecem a URL
# começando com "postgres://", mas o SQLAlchemy moderno espera
# "postgresql://". Corrigimos isso automaticamente aqui.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# connect_args só é necessário para o SQLite (não existe no Postgres).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency do FastAPI: abre uma sessão por requisição e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()