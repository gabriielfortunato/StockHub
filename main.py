from fastapi import FastAPI

from app.routes import auth, categorias, movimentacoes, produtos

app = FastAPI(
    title="StockHub",
    description="API de gestão de estoque para pequenas empresas",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(categorias.router)
app.include_router(produtos.router)
app.include_router(movimentacoes.router)


@app.get("/")
def raiz():
    return {"mensagem": "Bem-vindo ao StockHub!"}