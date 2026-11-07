from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.database.session import Base


class PagamentoProcessado(Base):
    __tablename__ = "pagamentos_processados"

    id = Column(Integer, primary_key=True, index=True)
    order_nsu = Column(String(80), unique=True, nullable=False, index=True)
    transaction_nsu = Column(String(120), unique=True, nullable=True, index=True)
    valor_centavos = Column(Integer, nullable=False)
    loja_id = Column(Integer, ForeignKey("lojas.id"), nullable=False, index=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    processado_em = Column(DateTime, nullable=True)
