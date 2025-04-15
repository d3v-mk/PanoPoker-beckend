# api/schemas.py
from pydantic import BaseModel
from typing import List, Optional


class UserCreate(BaseModel):
    username: str
    email: str
    password: str

    
class SaqueInput(BaseModel):
    valor: float

class MesaBase(BaseModel):
    id: int
    nome: str
    status: str
    jogadores: int 

    class Config:
        from_attributes = True

class Mesa(MesaBase):
    id: int
    nome: str
    status: str
    jogadores: int

    class Config:
        from_attributes = True