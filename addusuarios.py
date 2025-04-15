from db.database import SessionLocal
from db.models import User
from passlib.context import CryptContext

# Configura o contexto do PassLib com bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Cria a sessão do banco
db = SessionLocal()

# Lista de usuários para criar
usuarios = [
    {"username": "mk", "email": "jogador1@pano.com", "password": "123"},
    {"username": "mk2", "email": "jogador2@pano.com", "password": "123"},
    {"username": "mk3", "email": "jogador3@pano.com", "password": "123"},
]

for user_data in usuarios:
    existente = db.query(User).filter_by(email=user_data["email"]).first()
    if not existente:
        hashed_password = pwd_context.hash(user_data["password"])
        novo_user = User(
            username=user_data["username"],
            email=user_data["email"],
            password=hashed_password,  # aqui usamos 'password' porque é o nome do campo
            balance=100.0
        )
        db.add(novo_user)

db.commit()
db.close()

print("Usuários criados com sucesso!")
