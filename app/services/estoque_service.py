"""
Regras de negócio ligadas ao estoque.

Toda entrada ou saída de produto deve passar por aqui — nunca alterar
Produto.quantidade_atual diretamente numa rota. Isso garante que o
saldo do produto e o histórico de movimentações nunca fiquem
dessincronizados.
"""

from sqlalchemy.orm import Session

from app.models.movimentacao import MovimentacaoEstoque, TipoMovimentacao
from app.models.produto import Produto


class EstoqueInsuficienteError(Exception):
    """Levantado ao tentar dar saída em quantidade maior que o disponível."""

    def __init__(self, produto_id: int, disponivel: int, solicitado: int):
        self.produto_id = produto_id
        self.disponivel = disponivel
        self.solicitado = solicitado
        super().__init__(
            f"Estoque insuficiente para o produto {produto_id}: "
            f"disponível={disponivel}, solicitado={solicitado}"
        )


class ProdutoNaoEncontradoError(Exception):
    """Levantado quando o produto informado não existe (ou não é da loja)."""

    def __init__(self, produto_id: int):
        self.produto_id = produto_id
        super().__init__(f"Produto {produto_id} não encontrado")


def _buscar_produto_da_loja(db: Session, produto_id: int, loja_id: int) -> Produto:
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.loja_id == loja_id)
        .first()
    )
    if produto is None:
        raise ProdutoNaoEncontradoError(produto_id)
    return produto


def registrar_movimentacao(
    db: Session,
    *,
    produto_id: int,
    loja_id: int,
    tipo: TipoMovimentacao,
    quantidade: int,
    motivo: str | None = None,
) -> MovimentacaoEstoque:
    if quantidade <= 0:
        raise ValueError("quantidade deve ser maior que zero")

    produto = _buscar_produto_da_loja(db, produto_id, loja_id)

    if tipo == TipoMovimentacao.ENTRADA:
        produto.quantidade_atual += quantidade
    else:  # SAIDA
        if quantidade > produto.quantidade_atual:
            raise EstoqueInsuficienteError(
                produto_id=produto.id,
                disponivel=produto.quantidade_atual,
                solicitado=quantidade,
            )
        produto.quantidade_atual -= quantidade

    movimentacao = MovimentacaoEstoque(
        produto_id=produto.id,
        tipo=tipo,
        quantidade=quantidade,
        motivo=motivo,
    )

    db.add(movimentacao)
    db.add(produto)
    db.commit()
    db.refresh(movimentacao)
    db.refresh(produto)

    return movimentacao


def listar_produtos_abaixo_do_minimo(db: Session, loja_id: int) -> list[Produto]:
    return (
        db.query(Produto)
        .filter(
            Produto.loja_id == loja_id,
            Produto.quantidade_atual <= Produto.estoque_minimo,
        )
        .all()
    )