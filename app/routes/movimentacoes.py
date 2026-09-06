"""
Rotas de movimentação de estoque (entradas e saídas).

A lógica de negócio fica no estoque_service — aqui só traduzimos
os erros de negócio em respostas HTTP adequadas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.models.movimentacao import MovimentacaoEstoque, TipoMovimentacao
from app.services.estoque_service import (
    EstoqueInsuficienteError,
    ProdutoNaoEncontradoError,
    registrar_movimentacao,
)
from app.utils.deps import get_loja_atual

router = APIRouter(prefix="/movimentacoes", tags=["movimentacoes"])


class MovimentacaoCriar(BaseModel):
    produto_id: int
    tipo: TipoMovimentacao
    quantidade: int
    motivo: str | None = None


class MovimentacaoResposta(BaseModel):
    id: int
    produto_id: int
    tipo: TipoMovimentacao
    quantidade: int
    motivo: str | None

    class Config:
        from_attributes = True


@router.post("", response_model=MovimentacaoResposta, status_code=status.HTTP_201_CREATED)
def criar_movimentacao(
    dados: MovimentacaoCriar,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    try:
        movimentacao = registrar_movimentacao(
            db,
            produto_id=dados.produto_id,
            loja_id=loja_atual.id,
            tipo=dados.tipo,
            quantidade=dados.quantidade,
            motivo=dados.motivo,
        )
    except ProdutoNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(erro))
    except EstoqueInsuficienteError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    return movimentacao


@router.get("/produto/{produto_id}", response_model=list[MovimentacaoResposta])
def listar_movimentacoes_do_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    """Histórico de movimentações de um produto específico da loja logada."""
    return (
        db.query(MovimentacaoEstoque)
        .join(MovimentacaoEstoque.produto)
        .filter(
            MovimentacaoEstoque.produto_id == produto_id,
        )
        .filter_by(loja_id=loja_atual.id)  # via join, garante isolamento por loja
        .all()
    )