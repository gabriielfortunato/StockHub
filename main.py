import os

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import inspect, text

from app.database.session import Base, engine
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import assinatura, auth, categorias, equipe, movimentacoes, produtos, relatorios, webhooks

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    title="Stokfy",
    description="API de gestão de estoque para pequenas empresas",
    version="0.1.0",
)

class CabecalhosSegurancaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        if os.environ.get("RENDER", "").lower() == "true" or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path.startswith(("/auth/", "/produtos", "/categorias", "/movimentacoes", "/relatorios", "/equipe", "/admin")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(CabecalhosSegurancaMiddleware)

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
    """Adiciona colunas novas em bancos existentes, sem apagar dados."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "lojas" not in inspector.get_table_names():
        return
    colunas = {coluna["name"] for coluna in inspector.get_columns("lojas")}
    if "teste_gratis_iniciado_em" not in colunas:
        with engine.begin() as conexao:
            if engine.dialect.name == "postgresql":
                conexao.execute(text("ALTER TABLE lojas ADD COLUMN IF NOT EXISTS teste_gratis_iniciado_em TIMESTAMP NULL"))
            else:
                conexao.execute(text("ALTER TABLE lojas ADD COLUMN teste_gratis_iniciado_em TIMESTAMP NULL"))
            # Contas que receberam o teste automaticamente na versão anterior
            # são marcadas como já utilizadas para não reiniciar os 7 dias.
            if "teste_gratis_ate" in colunas:
                conexao.execute(text(
                    "UPDATE lojas SET teste_gratis_iniciado_em = teste_gratis_ate "
                    "WHERE teste_gratis_ate IS NOT NULL AND teste_gratis_iniciado_em IS NULL"
                ))
    if "produtos" in inspector.get_table_names():
        produto_colunas = {coluna["name"] for coluna in inspector.get_columns("produtos")}
        if "ativo" not in produto_colunas:
            with engine.begin() as conexao:
                if engine.dialect.name == "postgresql":
                    conexao.execute(text("ALTER TABLE produtos ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE"))
                else:
                    conexao.execute(text("ALTER TABLE produtos ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT 1"))

    if "movimentacoes_estoque" in inspector.get_table_names():
        mov_colunas = {coluna["name"] for coluna in inspector.get_columns("movimentacoes_estoque")}
        if "responsavel" not in mov_colunas:
            with engine.begin() as conexao:
                conexao.execute(text("ALTER TABLE movimentacoes_estoque ADD COLUMN responsavel VARCHAR(180) NULL"))

    if "teste_gratis_ate" not in colunas:
        with engine.begin() as conexao:
            if engine.dialect.name == "postgresql":
                conexao.execute(text("ALTER TABLE lojas ADD COLUMN IF NOT EXISTS teste_gratis_ate TIMESTAMP NULL"))
            else:
                conexao.execute(text("ALTER TABLE lojas ADD COLUMN teste_gratis_ate TIMESTAMP NULL"))

    if "ultima_atividade" not in colunas:
        with engine.begin() as conexao:
            if engine.dialect.name == "postgresql":
                conexao.execute(text("ALTER TABLE lojas ADD COLUMN IF NOT EXISTS ultima_atividade TIMESTAMP NULL"))
            else:
                conexao.execute(text("ALTER TABLE lojas ADD COLUMN ultima_atividade TIMESTAMP NULL"))


@app.get("/")
def raiz(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/termos")
def pagina_termos(request: Request):
    return templates.TemplateResponse("termos.html", {"request": request})


@app.get("/privacidade")
def pagina_privacidade(request: Request):
    return templates.TemplateResponse("privacidade.html", {"request": request})


@app.get("/boas-vindas")
def pagina_boas_vindas(request: Request):
    return templates.TemplateResponse("onboarding.html", {"request": request})


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


@app.get("/painel/relatorios")
def pagina_relatorios(request: Request):
    return templates.TemplateResponse("relatorios.html", {"request": request})


@app.get("/painel/equipe")
def pagina_equipe(request: Request):
    return templates.TemplateResponse("equipe.html", {"request": request})


@app.get("/login-funcionario")
def pagina_login_funcionario(request: Request):
    return templates.TemplateResponse("login_funcionario.html", {"request": request})


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


@app.get("/plano/regularizar")
def pagina_regularizar_plano(request: Request):
    return templates.TemplateResponse("regularizar_plano.html", {"request": request})


@app.get("/assinatura")
def pagina_assinatura(request: Request):
    return templates.TemplateResponse("assinatura.html", {"request": request})


@app.get("/admin")
def pagina_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})
