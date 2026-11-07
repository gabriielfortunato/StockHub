"""Relatórios, exportação e cópia de segurança por loja."""
import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.categoria import Categoria
from app.models.loja import Loja
from app.models.movimentacao import MovimentacaoEstoque
from app.models.produto import Produto
from app.utils.deps import get_loja_atual, get_loja_ativa

router = APIRouter(prefix="/relatorios", tags=["relatorios"])

@router.get("/resumo")
def resumo(db: Session = Depends(get_db), loja: Loja = Depends(get_loja_atual)):
    produtos = db.query(Produto).filter(Produto.loja_id == loja.id).all()
    movimentos = db.query(MovimentacaoEstoque).join(Produto).filter(Produto.loja_id == loja.id).all()
    entradas = sum(m.quantidade for m in movimentos if m.tipo.value == "entrada")
    saidas = sum(m.quantidade for m in movimentos if m.tipo.value == "saida")
    return {
        "total_produtos": len(produtos),
        "unidades_em_estoque": sum(p.quantidade_atual for p in produtos),
        "valor_estimado_estoque": round(sum(p.quantidade_atual * p.preco_custo for p in produtos), 2),
        "produtos_baixo_estoque": sum(1 for p in produtos if p.quantidade_atual <= p.estoque_minimo),
        "entradas_total": entradas,
        "saidas_total": saidas,
    }

@router.get("/movimentacoes")
def historico(db: Session = Depends(get_db), loja: Loja = Depends(get_loja_atual)):
    linhas = (
        db.query(MovimentacaoEstoque, Produto.nome, Produto.sku)
        .join(Produto, Produto.id == MovimentacaoEstoque.produto_id)
        .filter(Produto.loja_id == loja.id)
        .order_by(MovimentacaoEstoque.criado_em.desc())
        .limit(500)
        .all()
    )
    return [{
        "id": m.id, "produto": nome, "sku": sku, "tipo": m.tipo.value,
        "quantidade": m.quantidade, "motivo": m.motivo,
        "criado_em": m.criado_em.isoformat() if m.criado_em else None
    } for m, nome, sku in linhas]

@router.get("/produtos.csv")
def exportar_csv(db: Session = Depends(get_db), loja: Loja = Depends(get_loja_atual)):
    produtos = db.query(Produto).filter(Produto.loja_id == loja.id).order_by(Produto.nome).all()
    arquivo = io.StringIO()
    escritor = csv.writer(arquivo, delimiter=";")
    escritor.writerow(["SKU", "Produto", "Descrição", "Quantidade", "Estoque mínimo", "Preço de custo", "Preço de venda"])
    for p in produtos:
        escritor.writerow([p.sku or "", p.nome, p.descricao or "", p.quantidade_atual, p.estoque_minimo, p.preco_custo, p.preco_venda])
    conteudo = "\ufeff" + arquivo.getvalue()
    return StreamingResponse(iter([conteudo]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=stokfy-produtos.csv"})

@router.get("/backup")
def exportar_backup(db: Session = Depends(get_db), loja: Loja = Depends(get_loja_atual)):
    categorias = db.query(Categoria).filter(Categoria.loja_id == loja.id).all()
    produtos = db.query(Produto).filter(Produto.loja_id == loja.id).all()
    movimentos = db.query(MovimentacaoEstoque).join(Produto).filter(Produto.loja_id == loja.id).all()
    return {
        "formato": "stokfy-backup-v1", "gerado_em": datetime.utcnow().isoformat(),
        "categorias": [{"id": c.id, "nome": c.nome} for c in categorias],
        "produtos": [{"id": p.id, "nome": p.nome, "sku": p.sku, "descricao": p.descricao,
            "preco_custo": p.preco_custo, "preco_venda": p.preco_venda,
            "quantidade_atual": p.quantidade_atual, "estoque_minimo": p.estoque_minimo,
            "categoria_id": p.categoria_id} for p in produtos],
        "movimentacoes": [{"produto_id": m.produto_id, "tipo": m.tipo.value,
            "quantidade": m.quantidade, "motivo": m.motivo,
            "criado_em": m.criado_em.isoformat() if m.criado_em else None} for m in movimentos],
    }

class BackupRestaurar(BaseModel):
    backup: dict

@router.post("/restaurar")
def restaurar_backup(dados: BackupRestaurar, db: Session = Depends(get_db), loja: Loja = Depends(get_loja_ativa)):
    backup = dados.backup
    if backup.get("formato") != "stokfy-backup-v1":
        raise HTTPException(status_code=400, detail="Arquivo de backup inválido ou incompatível.")
    categorias_ids = {}
    produtos_ids = {}
    try:
        for item in backup.get("categorias", []):
            categoria = Categoria(nome=str(item["nome"])[:120], loja_id=loja.id)
            db.add(categoria); db.flush()
            categorias_ids[item.get("id")] = categoria.id
        for item in backup.get("produtos", []):
            categoria_id = categorias_ids.get(item.get("categoria_id"))
            produto = Produto(
                nome=str(item["nome"])[:180], sku=(item.get("sku") or None),
                descricao=(item.get("descricao") or None), preco_custo=max(0, float(item.get("preco_custo", 0))),
                preco_venda=max(0, float(item.get("preco_venda", 0))),
                quantidade_atual=max(0, int(item.get("quantidade_atual", 0))),
                estoque_minimo=max(0, int(item.get("estoque_minimo", 0))),
                categoria_id=categoria_id, loja_id=loja.id)
            db.add(produto); db.flush()
            produtos_ids[item.get("id")] = produto.id
        for item in backup.get("movimentacoes", []):
            produto_id = produtos_ids.get(item.get("produto_id"))
            if not produto_id: continue
            from app.models.movimentacao import TipoMovimentacao
            movimento = MovimentacaoEstoque(produto_id=produto_id,
                tipo=TipoMovimentacao(item["tipo"]), quantidade=max(1, int(item["quantidade"])),
                motivo=(item.get("motivo") or "Restaurado de backup")[:255])
            db.add(movimento)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível restaurar. Verifique o arquivo; nenhum dado foi importado.")
    return {"mensagem": "Backup restaurado. Os itens foram adicionados sem substituir os dados atuais."}
