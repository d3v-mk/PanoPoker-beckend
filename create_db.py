from db.database import Base, engine
from db.models import User

print("Criando o banco de dados...")

Base.metadata.create_all(bind=engine)

print("Banco criado com sucesso!")