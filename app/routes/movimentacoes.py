"""
Rotas de movimentação de estoque (entradas e saídas).
"""
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.loja import Loja
from app.models.movimentacao import MovimentacaoEstoque, TipoMovimentacao
from app.models.produto import Produto
from app.services.estoque_service import (
    EstoqueInsuficienteError,
    ProdutoNaoEncontradoError,
    registrar_movimentacao,
)
from app.utils.deps import get_loja_ativa, get_loja_atual

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


class ComandoTerminal(BaseModel):
    comando: str = Field(min_length=3, max_length=300)


def _normalizar_texto(valor: str) -> str:
    valor = unicodedata.normalize("NFKD", valor.casefold())
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", valor).strip()


def _interpretar_comando(comando: str) -> tuple[TipoMovimentacao, int, str]:
    texto = comando.strip()
    acao = re.match(
        r"^(venda|vender|vendi|saida|retirada|retirar|retire|remover|baixa|"
        r"entrada|adicionar|adicione|receber|receba|repor)\b\s*(.*)$",
        texto,
        flags=re.IGNORECASE,
    )
    if not acao:
        raise ValueError(
            "Não entendi a operação. Comece com 'vender', 'entrada' ou 'retirar'."
        )

    verbo = _normalizar_texto(acao.group(1))
    restante = re.sub(r"^de\s+", "", acao.group(2).strip(), flags=re.IGNORECASE)
    if verbo in {"entrada", "adicionar", "adicione", "receber", "receba", "repor"}:
        tipo = TipoMovimentacao.ENTRADA
    else:
        tipo = TipoMovimentacao.SAIDA

    # Formatos: "vender 3 unidades de Camiseta", "venda Camiseta, 3 unidades"
    padroes = [
        r"^(\d+)\s*(?:unidades?|un|itens?)?\s+(?:de|do|da|dos|das)\s+(.+)$",
        r"^(\d+)\s+(.+)$",
        r"^(.+?)[,;]\s*(\d+)\s*(?:unidades?|un|itens?)?$",
        r"^(.+?)\s+(\d+)\s*(?:unidades?|un|itens?)?$",
    ]

    quantidade = None
    produto = None
    for indice, padrao in enumerate(padroes):
        encontrado = re.match(padrao, restante, flags=re.IGNORECASE)
        if encontrado:
            if indice < 2:
                quantidade, produto = int(encontrado.group(1)), encontrado.group(2)
            else:
                produto, quantidade = encontrado.group(1), int(encontrado.group(2))
            break

    if quantidade is None or not produto:
        raise ValueError(
            "Informe a quantidade e o produto. Exemplo: 'vender 3 unidades de Camiseta'."
        )

    produto = re.sub(r"^(?:de|do|da|dos|das)\s+", "", produto.strip(), flags=re.IGNORECASE)
    produto = re.sub(r"\s+(?:unidades?|un|itens?)$", "", produto, flags=re.IGNORECASE).strip()
    if quantidade <= 0:
        raise ValueError("A quantidade precisa ser maior que zero.")
    if not produto:
        raise ValueError("Informe o nome do produto.")

    return tipo, quantidade, produto


@router.post("/terminal")
def executar_comando_terminal(
    dados: ComandoTerminal,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_ativa),
):
    """Interpreta um comando simples e registra a movimentação da loja autenticada."""
    try:
        tipo, quantidade, nome_produto = _interpretar_comando(dados.comando)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    termo = _normalizar_texto(nome_produto)
    produtos = db.query(Produto).filter(Produto.loja_id == loja_atual.id).all()

    correspondencias = [
        produto for produto in produtos
        if _normalizar_texto(produto.nome) == termo
        or (produto.sku and _normalizar_texto(produto.sku) == termo)
    ]

    if not correspondencias:
        parciais = [
            produto for produto in produtos
            if termo in _normalizar_texto(produto.nome)
        ]
        if len(parciais) == 1:
            correspondencias = parciais
        elif len(parciais) > 1:
            nomes = ", ".join(produto.nome for produto in parciais[:5])
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Encontrei mais de um produto parecido: {nomes}. Digite o nome completo.",
            )

    if not correspondencias:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Não encontrei o produto '{nome_produto}' nesta loja.",
        )
    if len(correspondencias) > 1:
        nomes = ", ".join(produto.nome for produto in correspondencias[:5])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O comando corresponde a mais de um produto: {nomes}. Informe o SKU ou nome completo.",
        )

    produto = correspondencias[0]
    estoque_anterior = produto.quantidade_atual
    try:
        movimentacao = registrar_movimentacao(
            db,
            produto_id=produto.id,
            loja_id=loja_atual.id,
            tipo=tipo,
            quantidade=quantidade,
            motivo=f"Terminal: {tipo.value}",
        )
    except ProdutoNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(erro))
    except EstoqueInsuficienteError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    db.refresh(produto)
    acao = "Entrada" if tipo == TipoMovimentacao.ENTRADA else "Venda/saída"
    return {
        "mensagem": f"{acao} registrada com sucesso.",
        "movimentacao_id": movimentacao.id,
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "tipo": tipo.value,
        "quantidade": quantidade,
        "estoque_anterior": estoque_anterior,
        "estoque_atual": produto.quantidade_atual,
    }


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
        .filter_by(loja_id=loja_atual.id)
        .all()
    )


@router.post("", response_model=MovimentacaoResposta, status_code=status.HTTP_201_CREATED)
def criar_movimentacao(
    dados: MovimentacaoCriar,
    db: Session = Depends(get_db),
    loja_atual: Loja = Depends(get_loja_ativa),
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
