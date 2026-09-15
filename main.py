from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import assinatura, auth, categorias, movimentacoes, produtos, webhooks

app = FastAPI(
    title="Stokfy",
    description="API de gestão de estoque para pequenas empresas",
    version="0.1.0",
)

# Registro dos roteadores
app.include_router(auth.router)
app.include_router(categorias.router)
app.include_router(produtos.router)
app.include_router(movimentacoes.router)
app.include_router(assinatura.router)
app.include_router(webhooks.router)

# Configuração de arquivos estáticos (CSS, JS) e templates HTML
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


@app.get("/renovar")
def pagina_renovar(request: Request):
    return templates.TemplateResponse("renovar.html", {"request": request})


@app.get("/assinatura")
def pagina_assinatura(request: Request):
    # Corrigido para "assinatura.html" com "a" minúsculo para compatibilidade com o Linux no Render
    return templates.TemplateResponse("assinatura.html", {"request": request})