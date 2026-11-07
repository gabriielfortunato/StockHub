"""
Rotas de CRUD de produtos e consulta de códigos de barras.
"""
import re

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.models.produto import Produto
from app.services.estoque_service import listar_produtos_abaixo_do_minimo
from app.utils.deps import get_loja_ativa, get_loja_atual
from app.utils.planos import LIMITES_PLANO_GRATUITO, loja_tem_plus

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
    ativo: bool = True
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


@router.get("/buscar-codigo/{codigo}")
def buscar_produto_por_codigo(
    codigo: str,
    loja_atual: Loja = Depends(get_loja_atual),
):
    """Consulta dados públicos do produto pelo EAN/GTIN na Open Food Facts."""
    codigo = codigo.strip()
    if not re.fullmatch(r"\d{8,14}", codigo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido. Informe um código de barras numérico de 8 a 14 dígitos.",
        )

    url = f"https://world.openfoodfacts.org/api/v2/product/{codigo}.json"
    try:
        resposta = requests.get(
            url,
            params={"fields": "product_name,product_name_pt,brands,quantity,categories"},
            headers={"User-Agent": "Stokfy/1.0 (https://stokfy.onrender.com)"},
            timeout=8,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível consultar a base de produtos agora. Tente novamente.",
        )

    if dados.get("status") != 1 or not dados.get("product"):
        return {"encontrado": False, "codigo": codigo}

    produto = dados["product"]
    nome = produto.get("product_name_pt") or produto.get("product_name") or ""
    marca = produto.get("brands") or ""
    quantidade = produto.get("quantity") or ""
    categorias = produto.get("categories") or ""

    partes_descricao = []
    if marca:
        partes_descricao.append(f"Marca: {marca}")
    if quantidade:
        partes_descricao.append(f"Conteúdo: {quantidade}")
    if categorias:
        categoria = categorias.split(",")[0].strip()
        if categoria:
            partes_descricao.append(f"Categoria informada: {categoria}")

    return {
        "encontrado": bool(nome),
        "codigo": codigo,
        "nome": nome,
        "descricao": " | ".join(partes_descricao),
    }


@router.post("", response_model=ProdutoResposta, status_code=status.HTTP_201_CREATED)
def criar_produto(
    dados: ProdutoCriar,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_ativa),
):
    if not loja_tem_plus(loja_atual):
        pendentes = db.query(Produto).filter(Produto.loja_id == loja_atual.id, Produto.ativo.is_(True)).count()
        if pendentes > LIMITES_PLANO_GRATUITO["produtos"]:
            raise HTTPException(status_code=409, detail="Escolha até 10 produtos para manter ativos antes de continuar usando o plano gratuito.")
        total_atual = pendentes
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
    return db.query(Produto).filter(Produto.loja_id == loja_atual.id, Produto.ativo.is_(True)).all()


@router.get("/regularizacao", response_model=list[ProdutoResposta])
def listar_produtos_para_regularizacao(
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_atual),
):
    if loja_tem_plus(loja_atual):
        raise HTTPException(status_code=409, detail="Sua loja possui acesso ao Plus e não precisa regularizar o plano.")
    return db.query(Produto).filter(Produto.loja_id == loja_atual.id).order_by(Produto.nome).all()


class RegularizarProdutos(BaseModel):
    produtos_ativos: list[int]


@router.post("/regularizacao")
def regularizar_produtos(
    dados: RegularizarProdutos,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_ativa),
):
    if loja_tem_plus(loja_atual):
        raise HTTPException(status_code=409, detail="Sua loja possui acesso ao Plus.")
    limite = LIMITES_PLANO_GRATUITO["produtos"]
    ids = list(dict.fromkeys(dados.produtos_ativos))
    if len(ids) > limite:
        raise HTTPException(status_code=400, detail=f"Selecione no máximo {limite} produtos.")
    produtos = db.query(Produto).filter(Produto.loja_id == loja_atual.id).all()
    ids_existentes = {produto.id for produto in produtos}
    if any(produto_id not in ids_existentes for produto_id in ids):
        raise HTTPException(status_code=400, detail="A seleção contém produtos inválidos.")
    for produto in produtos:
        produto.ativo = produto.id in ids
    db.commit()
    return {"mensagem": "Plano gratuito regularizado. Os demais produtos foram arquivados e continuam salvos.", "ativos": len(ids), "arquivados": len(produtos) - len(ids)}


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
    loja_atual: Loja = Depends(get_loja_ativa),
):
    produto = _buscar_ou_404(db, produto_id, loja_atual.id)
    if not loja_tem_plus(loja_atual) and db.query(Produto).filter(Produto.loja_id == loja_atual.id, Produto.ativo.is_(True)).count() > LIMITES_PLANO_GRATUITO["produtos"]:
        raise HTTPException(status_code=409, detail="Regularize sua seleção de até 10 produtos antes de editar o estoque.")
    if not produto.ativo:
        raise HTTPException(status_code=403, detail="Este produto está arquivado. Reative-o ao liberar uma vaga no plano gratuito.")

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
    loja_atual: Loja = Depends(get_loja_ativa),
):
    produto = _buscar_ou_404(db, produto_id, loja_atual.id)
    db.delete(produto)
    db.commit()
