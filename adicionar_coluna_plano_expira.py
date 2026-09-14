"""
Adiciona a coluna 'plano_expira_em' na tabela 'lojas'.

Rode localmente:
    python adicionar_coluna_plano_expira.py

E depois contra o Neon (configurando a DATABASE_URL antes, como já
fizemos com o adicionar_coluna_plano.py):
    $env:DATABASE_URL = 'sua-connection-string-do-neon'
    python adicionar_coluna_plano_expira.py
"""

from sqlalchemy import text

from app.database.session import engine

SQL = """
ALTER TABLE lojas
ADD COLUMN plano_expira_em TIMESTAMP NULL
"""

if __name__ == "__main__":
    try:
        with engine.connect() as conexao:
            conexao.execute(text(SQL))
            conexao.commit()
        print("Coluna 'plano_expira_em' adicionada com sucesso.")
    except Exception as erro:
        if "duplicate column" in str(erro).lower() or "already exists" in str(erro).lower():
            print("A coluna 'plano_expira_em' já existia. Nada a fazer.")
        else:
            raise