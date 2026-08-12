from app.database.session import Base, engine
from app import models  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Banco de dados criado em estoque.db")