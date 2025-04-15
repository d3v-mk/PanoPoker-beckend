from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Caminho absoluto para o banco de dados na pasta data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'panopoker.db')
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Conectando com o banco
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Sessão com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base dos modelos
Base = declarative_base()

# Função para obter sessão com o banco (dependência do FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
