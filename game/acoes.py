from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Mesa, JogadorNaMesa, SidePot, User
from game.partida import ControladorDePartida, get_jogadores_da_mesa
from api.auth import get_current_user

router = APIRouter(prefix="/mesas", tags=["Ações de Jogo"])


def get_jogador(db: Session, mesa_id: int, user_id: int) -> JogadorNaMesa:
    jogador = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id, user_id=user_id).first()
    if not jogador:
        raise HTTPException(status_code=404, detail="Jogador não encontrado na mesa.")
    return jogador


def get_mesa(db: Session, mesa_id: int) -> Mesa:
    mesa = db.query(Mesa).filter_by(id=mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")
    return mesa


def verificar_vez(jogador: JogadorNaMesa, mesa: Mesa):
    if jogador.user_id != mesa.jogador_da_vez_id:
        raise HTTPException(status_code=403, detail="Não é sua vez de jogar.")


@router.post("/{mesa_id}/call")
def call(mesa_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, current_user.id)
    verificar_vez(jogador, mesa)

    valor_para_pagar = mesa.aposta_atual - jogador.aposta_atual
    if valor_para_pagar <= 0:
        raise HTTPException(status_code=400, detail="Nenhuma aposta para pagar.")

    if jogador.stack < valor_para_pagar:
        valor_real = jogador.stack
        jogador.aposta_atual += valor_real
        jogador.stack = 0
        jogador.saldo_restante = 0
    else:
        jogador.stack -= valor_para_pagar
        jogador.aposta_atual += valor_para_pagar
        jogador.saldo_restante = jogador.stack

    jogador.rodada_ja_agiu = True
    db.commit()

    jogadores = get_jogadores_da_mesa(mesa_id, db)
    controlador = ControladorDePartida(mesa, jogadores, db)
    controlador.verificar_proxima_etapa()
    controlador.avancar_vez()

    return {"msg": f"Call de R${valor_para_pagar:.2f}"}


@router.post("/{mesa_id}/check")
def check(mesa_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, current_user.id)
    verificar_vez(jogador, mesa)

    if jogador.aposta_atual != mesa.aposta_atual:
        raise HTTPException(status_code=400, detail="Você não pode dar check. Há uma aposta maior que a sua.")
    
    jogador.rodada_ja_agiu = True
    db.commit()

    jogadores = get_jogadores_da_mesa(mesa_id, db)
    controlador = ControladorDePartida(mesa, jogadores, db)
    controlador.verificar_proxima_etapa()
    controlador.avancar_vez()

    return {"msg": "Check realizado com sucesso!"}


@router.post("/{mesa_id}/raise")
def raise_aposta(mesa_id: int, valor: float, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, current_user.id)
    verificar_vez(jogador, mesa)

    valor_total = mesa.aposta_atual + valor
    if jogador.stack < (valor_total - jogador.aposta_atual):
        raise HTTPException(status_code=400, detail="Stack insuficiente para raise.")

    valor_a_contribuir = valor_total - jogador.aposta_atual
    jogador.stack -= valor_a_contribuir
    jogador.aposta_atual = valor_total
    jogador.saldo_restante = jogador.stack
    mesa.aposta_atual = valor_total

    jogador.rodada_ja_agiu = True
    db.commit()

    jogadores = get_jogadores_da_mesa(mesa_id, db)
    controlador = ControladorDePartida(mesa, jogadores, db)
    controlador.verificar_proxima_etapa()
    controlador.avancar_vez()

    return {"msg": f"Raise para R${valor_total:.2f}"}


@router.post("/{mesa_id}/allin")
def allin(mesa_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, current_user.id)
    verificar_vez(jogador, mesa)

    if jogador.stack <= 0:
        raise HTTPException(status_code=400, detail="Você já está all-in ou sem stack.")

    valor_allin = jogador.stack
    jogador.aposta_atual += valor_allin
    jogador.stack = 0
    jogador.saldo_restante = 0

    if jogador.aposta_atual > mesa.aposta_atual:
        mesa.aposta_atual = jogador.aposta_atual

    if valor_allin < mesa.aposta_atual:
        side_pot_valor = mesa.aposta_atual - valor_allin
        side_pot = SidePot(mesa_id=mesa.id, jogador_id=jogador.id, valor=side_pot_valor)
        db.add(side_pot)

    jogador.rodada_ja_agiu = True
    db.commit()

    jogadores = get_jogadores_da_mesa(mesa_id, db)
    controlador = ControladorDePartida(mesa, jogadores, db)
    controlador.verificar_proxima_etapa()
    controlador.avancar_vez()

    return {"msg": f"All-in com R${valor_allin:.2f}"}


@router.post("/{mesa_id}/fold")
def fold(mesa_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mesa = get_mesa(db, mesa_id)
    jogador = get_jogador(db, mesa_id, current_user.id)
    verificar_vez(jogador, mesa)

    jogador.foldado = True

    jogador.rodada_ja_agiu = True
    db.commit()

    jogadores = get_jogadores_da_mesa(mesa_id, db)
    controlador = ControladorDePartida(mesa, jogadores, db)
    controlador.verificar_proxima_etapa()
    controlador.avancar_vez()

    return {"msg": "Você deu fold e saiu desta rodada."}
