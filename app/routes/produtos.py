"""
Rotas de CRUD de produtos.

Todas as consultas são filtradas por loja_id (via get_loja_atual),
garantindo que uma loja nunca veja ou altere produtos de outra.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.models.produto import Produto
from app.services.estoque_service import listar_produtos_abaixo_do_minimo
from app.utils.deps import get_loja_atual
from app.utils.planos import LIMITES_PLANO_GRATUITO, PLANO_GRATUITO

router = APIRouter(prefix="/produtos", tags=["produtos"])


class ProdutoCriar(BaseModel):
    nome: str
    sku: str | None = None
    descricao: str | None = None
    preco_custo: float = 0.0
    preco_venda: float = 0.0
    estoque_minimo: int = 0
    categoria_id: int | None = None


class ProdutoAtualizar(BaseModel):
    nome: str | None = None
    sku: str | None = None
    descricao: str | None = None
    preco_custo: float | None = None
    preco_venda: float | None = None
    estoque_minimo: int | None = None
    categoria_id: int | None = None


class ProdutoResposta(BaseModel):
    id: int
    nome: str
    sku: str | None
    descricao: str | None
    preco_custo: float
    preco_venda: float
    quantidade_atual: int
    estoque_minimo: int
    categoria_id: int | None

    class Config:
        from_attributes = True


def _buscar_ou_404(db: Session, produto_id: int, loja_id: int) -> Produto:
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.loja_id == loja_id)
        .first()
    )
    if produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    return produto


@router.post("", response_model=ProdutoResposta, status_code=status.HTTP_201_CREATED)
def criar_produto(
    dados: ProdutoCriar,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    if loja_atual.plano == PLANO_GRATUITO:
        total_atual = db.query(Produto).filter(Produto.loja_id == loja_atual.id).count()
        limite = LIMITES_PLANO_GRATUITO["produtos"]
        if total_atual >= limite:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"O plano gratuito permite no máximo {limite} produtos. Faça upgrade para o plano Plus para cadastrar mais.",
            )

    produto = Produto(**dados.model_dump(), loja_id=loja_atual.id)
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@router.get("", response_model=list[ProdutoResposta])
def listar_produtos(
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    return db.query(Produto).filter(Produto.loja_id == loja_atual.id).all()


@router.get("/abaixo-do-minimo", response_model=list[ProdutoResposta])
def produtos_abaixo_do_minimo(
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    """Lista os produtos que precisam de reposição (alerta de estoque)."""
    return listar_produtos_abaixo_do_minimo(db, loja_atual.id)


@router.get("/{produto_id}", response_model=ProdutoResposta)
def obter_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    return _buscar_ou_404(db, produto_id, loja_atual.id)


@router.put("/{produto_id}", response_model=ProdutoResposta)
def atualizar_produto(
    produto_id: int,
    dados: ProdutoAtualizar,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    produto = _buscar_ou_404(db, produto_id, loja_atual.id)

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)

    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    produto = _buscar_ou_404(db, produto_id, loja_atual.id)
    db.delete(produto)
    db.commit()