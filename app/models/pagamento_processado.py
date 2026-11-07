from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.database.session import Base


class PagamentoProcessado(Base):
    __tablename__ = "pagamentos_processados"

    id = Column(Integer, primary_key=True, index=True)
    transaction_nsu = Column(String(120), unique=True, nullable=False, index=True)
    loja_id = Column(Integer, ForeignKey("lojas.id"), nullable=False, index=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
