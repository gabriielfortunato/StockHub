"""
Model de Produto.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.session import Base


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(180), nullable=False)
    sku = Column(String(60), index=True, nullable=True)
    descricao = Column(String(500), nullable=True)

    preco_custo = Column(Float, default=0.0, nullable=False)
    preco_venda = Column(Float, default=0.0, nullable=False)

    quantidade_atual = Column(Integer, default=0, nullable=False)
    estoque_minimo = Column(Integer, default=0, nullable=False)

    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    loja_id = Column(Integer, ForeignKey("lojas.id"), nullable=False)
    loja = relationship("Loja", back_populates="produtos")

    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    categoria = relationship("Categoria", back_populates="produtos")

    movimentacoes = relationship(
        "MovimentacaoEstoque", back_populates="produto", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Produto id={self.id} nome={self.nome!r} qtd={self.quantidade_atual}>"