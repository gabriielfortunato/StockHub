"""
Model de Categoria.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.session import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)

    loja_id = Column(Integer, ForeignKey("lojas.id"), nullable=False)
    loja = relationship("Loja", back_populates="categorias")

    produtos = relationship("Produto", back_populates="categoria")

    def __repr__(self) -> str:
        return f"<Categoria id={self.id} nome={self.nome!r}>"