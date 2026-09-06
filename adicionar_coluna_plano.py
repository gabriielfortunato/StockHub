"""
Adiciona a coluna 'plano' na tabela 'lojas', sem apagar nada que já existe.

Rode uma vez localmente (usa o SQLite por padrão):
    python adicionar_coluna_plano.py

E rode uma vez contra o banco do Neon também, configurando a
DATABASE_URL antes (igual fizemos com o create_db.py):
    $env:DATABASE_URL = 'sua-connection-string-do-neon'
    python adicionar_coluna_plano.py
"""

from sqlalchemy import text

from app.database.session import engine

SQL = """
ALTER TABLE lojas
ADD COLUMN plano VARCHAR(20) NOT NULL DEFAULT 'gratuito'
"""

if __name__ == "__main__":
    try:
        with engine.connect() as conexao:
            conexao.execute(text(SQL))
            conexao.commit()
        print("Coluna 'plano' adicionada com sucesso.")
    except Exception as erro:
        # Se a coluna já existir, o banco vai reclamar — nesse caso, tudo bem.
        if "duplicate column" in str(erro).lower() or "already exists" in str(erro).lower():
            print("A coluna 'plano' já existia. Nada a fazer.")
        else:
            raise