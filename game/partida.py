from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from db.models import Mesa, JogadorNaMesa, User
import random

router = APIRouter()


def definir_blinds(mesa: Mesa, jogadores: list[JogadorNaMesa], db: Session):
    print(">>> DEFININDO BLINDS")

    # Verifica o valor mínimo da mesa e define os blinds
    if mesa.valor_minimo == 0.30:  # Ex: mesa bronze
        small_blind_valor = 0.01
        big_blind_valor = 0.02
    else:
        small_blind_valor = round(mesa.valor_minimo * 0.1, 2)
        big_blind_valor = round(mesa.valor_minimo * 0.2, 2)

    # Sorteia posições dos blinds
    posicoes = list(range(len(jogadores)))
    small_blind_index = random.choice(posicoes)
    big_blind_index = (small_blind_index + 1) % len(jogadores)

    jogador_small = jogadores[small_blind_index]
    jogador_big = jogadores[big_blind_index]

    # Checa stack
    if jogador_small.stack < small_blind_valor:
        raise HTTPException(status_code=400, detail="Small blind sem stack suficiente")
    if jogador_big.stack < big_blind_valor:
        raise HTTPException(status_code=400, detail="Big blind sem stack suficiente")

    # Atualiza jogadores
    jogador_small.stack -= small_blind_valor
    jogador_small.aposta_atual = small_blind_valor

    jogador_big.stack -= big_blind_valor
    jogador_big.aposta_atual = big_blind_valor

    db.add(jogador_small)
    db.add(jogador_big)

    # Atualiza mesa
    mesa.small_blind_pos = small_blind_index
    mesa.big_blind_pos = big_blind_index
    mesa.small_blind = small_blind_valor
    mesa.big_blind = big_blind_valor
    mesa.aposta_atual = big_blind_valor  # A aposta atual da mesa começa no big blind

    db.add(mesa)
    db.commit()
    db.refresh(mesa)

    print(">>> Blinds definidos com sucesso!")
