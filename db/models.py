from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Boolean
from .database import Base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

# Modelo de Usuários
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    balance = Column(Float, default=0.0)
    is_admin = Column(Boolean, default=False)
    transactions = relationship("Transaction", back_populates="user")
    jogadores_na_mesa = relationship("JogadorNaMesa", back_populates="user")
    


# Modelo de Transações
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    valor = Column(Float, nullable=False)
    tipo = Column(String, nullable=False)  # 'deposit' ou 'withdraw'
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)
    saldo_restante = Column(Float)

    user = relationship("User", back_populates="transactions")


# ENUM para status da mesa
class MesaStatus(str, enum.Enum):
    aberta = "aberta"
    em_jogo = "em_jogo"
    encerrada = "encerrada"


class Mesa(Base):
    __tablename__ = "mesas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    status = Column(Enum(MesaStatus), default=MesaStatus.aberta)
    limite_jogadores = Column(Integer, default=6)
    tipo_jogo = Column(String, default="Texas Hold'em")
    valor_minimo_aposta = Column(Float)
    valor_minimo = Column(Float)
    aposta_atual = Column(Float, default=0.0)
    small_blind_pos = Column(Integer, nullable=True)
    big_blind_pos = Column(Integer, nullable=True)
    small_blind = Column(Float, nullable=False)
    big_blind = Column(Float, nullable=False)
    side_pots = relationship("SidePot", back_populates="mesa")
    jogadores = relationship("JogadorNaMesa", back_populates="mesa")



# Modelo de Jogadores na Mesa
class JogadorNaMesa(Base):
    __tablename__ = "jogadores_na_mesa"

    id = Column(Integer, primary_key=True, index=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    stack_inicial = Column(Float)  # Aqui está o campo stack_inicial
    saldo_restante = Column(Float)
    aposta_atual = Column(Float, default=0.0)
    stack = Column(Float, default=0.0)
    mesa = relationship("Mesa", back_populates="jogadores")
    user = relationship("User", back_populates="jogadores_na_mesa")
    foldado = Column(Boolean, default=False)
    side_pots = relationship("SidePot", back_populates="jogador")






class SidePot(Base):
    __tablename__ = "side_pots"
    id = Column(Integer, primary_key=True, index=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"))
    jogador_id = Column(Integer, ForeignKey("jogadores_na_mesa.id"))  # Corrigido para 'jogadores_na_mesa.id'
    valor = Column(Float)

    mesa = relationship("Mesa", back_populates="side_pots")
    jogador = relationship("JogadorNaMesa", back_populates="side_pots")

