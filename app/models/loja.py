"""
Model da Loja.

Cada loja é o "tenant" do sistema: possui seu próprio login e só
enxerga seus próprios produtos e movimentações de estoque.

O campo `plano` controla os limites de uso: "gratuito" (limitado) ou
"plus" (ilimitado, pago).
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database.session import Base


class Loja(Base):
    __tablename__ = "lojas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)

    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    # "gratuito" ou "plus" — controla os limites de produtos/categorias.
    plano = Column(String(20), default="gratuito", nullable=False)

    produtos = relationship(
        "Produto", back_populates="loja", cascade="all, delete-orphan"
    )
    categorias = relationship(
        "Categoria", back_populates="loja", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Loja id={self.id} nome={self.nome!r} plano={self.plano!r}>"