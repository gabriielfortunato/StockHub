"""
Model de MovimentacaoEstoque.
"""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.session import Base


class TipoMovimentacao(str, enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacoes_estoque"

    id = Column(Integer, primary_key=True, index=True)

    tipo = Column(Enum(TipoMovimentacao), nullable=False)
    quantidade = Column(Integer, nullable=False)
    motivo = Column(String(255), nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    produto = relationship("Produto", back_populates="movimentacoes")

    def __repr__(self) -> str:
        return f"<Movimentacao {self.tipo} qtd={self.quantidade} produto_id={self.produto_id}>"