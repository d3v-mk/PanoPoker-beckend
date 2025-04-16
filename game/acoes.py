from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Mesa, JogadorNaMesa, SidePot

router = APIRouter(prefix="/mesas", tags=["Ações de Jogo"])

def get_jogador(db: Session, mesa_id: int, jogador_id: int) -> JogadorNaMesa:
    jogador = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id, id=jogador_id).first()
    if not jogador:
        raise HTTPException(status_code=404, detail="Jogador não encontrado na mesa.")
    return jogador

def get_mesa(db: Session, mesa_id: int) -> Mesa:
    mesa = db.query(Mesa).filter_by(id=mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")
    return mesa


@router.post("/{mesa_id}/jogadores/{jogador_id}/call")
def call(mesa_id: int, jogador_id: int, db: Session = Depends(get_db)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, jogador_id)

    valor_para_pagar = mesa.aposta_atual - jogador.aposta_atual

    if valor_para_pagar <= 0:
        raise HTTPException(status_code=400, detail="Nenhuma aposta para pagar.")

    if jogador.stack < valor_para_pagar:
        # All-in automático
        valor_real = jogador.stack
        jogador.aposta_atual += valor_real
        jogador.stack = 0
        jogador.saldo_restante = 0
        db.commit()
        return {"msg": f"All-in automático de R${valor_real:.2f}"}

    jogador.stack -= valor_para_pagar
    jogador.aposta_atual += valor_para_pagar
    jogador.saldo_restante = jogador.stack

    db.commit()
    return {"msg": f"Call de R${valor_para_pagar:.2f}"}


@router.post("/{mesa_id}/jogadores/{jogador_id}/check")
def check(mesa_id: int, jogador_id: int, db: Session = Depends(get_db)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, jogador_id)

    if jogador.aposta_atual != mesa.aposta_atual:
        raise HTTPException(status_code=400, detail="Você não pode dar check. Há uma aposta maior que a sua.")

    return {"msg": "Check realizado com sucesso!"}


@router.post("/{mesa_id}/jogadores/{jogador_id}/raise")
def raise_aposta(mesa_id: int, jogador_id: int, valor: float, db: Session = Depends(get_db)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, jogador_id)

    valor_total = mesa.aposta_atual + valor
    if jogador.stack < (valor_total - jogador.aposta_atual):
        raise HTTPException(status_code=400, detail="Stack insuficiente para raise.")

    valor_a_contribuir = valor_total - jogador.aposta_atual
    jogador.stack -= valor_a_contribuir
    jogador.aposta_atual = valor_total
    jogador.saldo_restante = jogador.stack
    mesa.aposta_atual = valor_total  # Atualiza aposta atual da mesa

    db.commit()
    return {"msg": f"Raise para R${valor_total:.2f}"}


@router.post("/{mesa_id}/jogadores/{jogador_id}/allin")
def allin(mesa_id: int, jogador_id: int, db: Session = Depends(get_db)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, jogador_id)

    if jogador.stack <= 0:
        raise HTTPException(status_code=400, detail="Você já está all-in ou sem stack.")

    valor_allin = jogador.stack
    jogador.aposta_atual += valor_allin
    jogador.saldo_restante = 0
    jogador.stack = 0

    # Atualiza aposta atual da mesa se o valor do all-in for maior
    if jogador.aposta_atual > mesa.aposta_atual:
        mesa.aposta_atual = jogador.aposta_atual

    # Adiciona o side pot, se necessário
    if valor_allin < mesa.aposta_atual:
        side_pot_valor = mesa.aposta_atual - valor_allin
        side_pot = SidePot(mesa_id=mesa.id, jogador_id=jogador.id, valor=side_pot_valor)
        db.add(side_pot)

    db.commit()
    return {"msg": f"All-in com R${valor_allin:.2f}"}


@router.post("/{mesa_id}/jogadores/{jogador_id}/fold")
def fold(mesa_id: int, jogador_id: int, db: Session = Depends(get_db)):
    jogador = get_jogador(db, mesa_id, jogador_id)
    jogador.foldado = True  # Marca o jogador como foldado
    db.commit()
    return {"msg": "Você deu fold e saiu desta rodada."}
