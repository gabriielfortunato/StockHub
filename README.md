# Stokfy

Micro-SaaS de gestão de estoque para pequenas empresas.

## O que é

O Stokfy permite que cada loja cadastre seus próprios produtos e categorias,
e registre entradas e saídas de estoque, com alertas automáticos de estoque
mínimo. Cada loja tem seu próprio login e só enxerga seus próprios dados.

## Stack

- **Backend:** Python 3.14 + FastAPI + SQLAlchemy
- **Banco de dados:** SQLite (desenvolvimento) / PostgreSQL via Neon (produção)
- **Autenticação:** JWT (python-jose) + hash de senha (passlib/bcrypt)
- **Frontend:** HTML + CSS + JavaScript puro, com templates Jinja2

## Rodando localmente

```bash
pip install -r requirements.txt
python create_db.py
python -m uvicorn main:app --reload
```

Depois, acesse `http://127.0.0.1:8000/cadastro` para criar sua primeira loja.

## Variáveis de ambiente (produção)

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | Connection string do Postgres (ex: Neon) |
| `SECRET_KEY` | Chave secreta usada para assinar os tokens JWT |