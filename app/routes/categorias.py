"""
Rotas de categorias — cada loja cadastra e gerencia as suas próprias.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.categoria import Categoria
from app.models.loja import Loja
from app.utils.deps import get_loja_atual

router = APIRouter(prefix="/categorias", tags=["categorias"])


class CategoriaCriar(BaseModel):
    nome: str


class CategoriaResposta(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True


@router.post("", response_model=CategoriaResposta, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    dados: CategoriaCriar,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    categoria = Categoria(nome=dados.nome, loja_id=loja_atual.id)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.get("", response_model=list[CategoriaResposta])
def listar_categorias(
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    return db.query(Categoria).filter(Categoria.loja_id == loja_atual.id).all()


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    categoria = (
        db.query(Categoria)
        .filter(Categoria.id == categoria_id, Categoria.loja_id == loja_atual.id)
        .first()
    )
    if categoria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")

    db.delete(categoria)
    db.commit()