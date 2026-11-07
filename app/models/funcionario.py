"""Contas de funcionários vinculadas a uma loja."""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.session import Base

class Funcionario(Base):
    __tablename__ = "funcionarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    pode_visualizar = Column(Boolean, default=True, nullable=False)
    pode_editar = Column(Boolean, default=False, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    loja_id = Column(Integer, ForeignKey("lojas.id"), nullable=False)
    loja = relationship("Loja", back_populates="funcionarios")
