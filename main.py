"""
Ponto de entrada da aplicação Stokfy.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import auth, categorias, movimentacoes, produtos

app = FastAPI(
    title="Stokfy",
    description="API de gestão de estoque para pequenas empresas",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(categorias.router)
app.include_router(produtos.router)
app.include_router(movimentacoes.router)

# Arquivos estáticos (CSS, JS) ficam disponíveis em /static/...
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def raiz():
    return {"mensagem": "Bem-vindo ao Stokfy!"}


@app.get("/login")
def pagina_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/painel")
def pagina_painel(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/cadastro")
def pagina_cadastro(request: Request):
    return templates.TemplateResponse("cadastro.html", {"request": request})

@app.get("/painel/categorias")
def pagina_categorias(request: Request):
    return templates.TemplateResponse("categorias.html", {"request": request})