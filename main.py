from fastapi import FastAPI, Request
from sqlalchemy import inspect, text

from app.database.session import Base, engine
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import assinatura, auth, categorias, equipe, movimentacoes, produtos, relatorios, webhooks

app = FastAPI(
    title="Stokfy",
    description="API de gestão de estoque para pequenas empresas",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(categorias.router)
app.include_router(produtos.router)
app.include_router(movimentacoes.router)
app.include_router(assinatura.router)
app.include_router(webhooks.router)
app.include_router(relatorios.router)
app.include_router(equipe.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def garantir_coluna_ultima_atividade():
    """Adiciona a coluna de presença em bancos já existentes, sem apagar dados."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "lojas" not in inspector.get_table_names():
        return
    colunas = {coluna["name"] for coluna in inspector.get_columns("lojas")}
    if "ultima_atividade" not in colunas:
        with engine.begin() as conexao:
            if engine.dialect.name == "postgresql":
                conexao.execute(text(
                    "ALTER TABLE lojas ADD COLUMN IF NOT EXISTS ultima_atividade TIMESTAMP NULL"
                ))
            else:
                conexao.execute(text(
                    "ALTER TABLE lojas ADD COLUMN ultima_atividade TIMESTAMP NULL"
                ))


@app.get("/")
def raiz():
    return {"mensagem": "Bem-vindo ao Stokfy!"}


@app.get("/login")
def pagina_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/recuperar-senha")
def pagina_recuperar_senha(request: Request):
    return templates.TemplateResponse("recuperar_senha.html", {"request": request})


@app.get("/redefinir-senha")
def pagina_redefinir_senha(request: Request):
    return templates.TemplateResponse("redefinir_senha.html", {"request": request})


@app.get("/painel")
def pagina_painel(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/painel/terminal")
def pagina_terminal(request: Request):
    return templates.TemplateResponse("terminal.html", {"request": request})


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
    return templates.TemplateResponse("assinatura.html", {"request": request})



@app.get("/admin")
def pagina_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})
