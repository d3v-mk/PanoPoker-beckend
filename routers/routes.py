'''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from db.database import SessionLocal, get_db
from db.models import User
from api.auth import hash_password, verify_password, create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordBearer
from api.schemas import UserCreate
from game.lobby import router as lobby_router 


# Instanciando o OAuth2PasswordBearer para obter o token do cabeçalho Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Router principal da API
router = APIRouter()

#Router para o lobby
router.include_router(lobby_router)

# Dependência para verificar o token JWT
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    user = db.query(User).filter(User.username == payload["sub"]).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

# Dependência para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelo de entrada para registro de usuário
class UserInput(BaseModel):
    username: str
    email: EmailStr
    password: str


# Rota de registro de usuário
@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Verificar se o email já existe
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Este email já está em uso.")

    hashed_password = hash_password(user.password)  # Sua função para criptografar a senha

    new_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password,
        balance=0.0,
        is_admin=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"msg": "Usuário criado com sucesso!"}


# Rota de login de usuário
@router.post("/login")
def login_user(user: UserInput, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Senha inválida")
    
    # Agora usando o ID no token
    access_token = create_access_token(user_id=db_user.id)
    
    return {
        "msg": f"Bem-vindo de volta, {db_user.username}!",
        "access_token": access_token,
        "token_type": "bearer"
    }


# Rota para ver o saldo
@router.get("/balance")
def get_balance(current_user: User = Depends(get_current_user)):
    return {"balance": current_user.balance}'''

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from db.database import SessionLocal, get_db
from db.models import User
from api.auth import hash_password, verify_password, create_access_token, decode_access_token
from api.schemas import UserCreate

# Rotas de outros módulos
from game.lobby import router as lobby_router
from game.mesas import router as mesas_router
from game.partida import router as partida_router
from game.acoes import router as acoes_router
from api.mercadopago_ipn import router as mp_router
from api.historico_transacoes import router as historico_router
from api.saque import router as saque_router
from api.depositar import router as depositar_router

router = APIRouter()

# Inclui sub-rotas
router.include_router(lobby_router)
router.include_router(mesas_router)
router.include_router(partida_router)
router.include_router(acoes_router)
router.include_router(mp_router)
router.include_router(historico_router)
router.include_router(saque_router)
router.include_router(depositar_router)

# Auth e user
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    user = db.query(User).filter(User.username == payload["sub"]).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

class UserInput(BaseModel):
    username: str
    email: EmailStr
    password: str

@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Este email já está em uso.")

    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password,
        balance=0.0,
        is_admin=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"msg": "Usuário criado com sucesso!"}

@router.post("/login")
def login_user(user: UserInput, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Senha inválida")
    
    access_token = create_access_token(user_id=db_user.id)
    
    return {
        "msg": f"Bem-vindo de volta, {db_user.username}!",
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/balance")
def get_balance(current_user: User = Depends(get_current_user)):
    return {"balance": current_user.balance}


