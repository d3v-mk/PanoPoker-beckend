from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Mesa, User, JogadorNaMesa, MesaStatus
from api.auth import get_current_user
from game.partida import iniciar_partida, get_mesa, get_jogadores_da_mesa, ControladorDePartida



router = APIRouter(prefix="/mesas", tags=["Mesas"])


# Entrar na mesa
@router.post("/{mesa_id}/jogadores/{jogador_id}/entrar")
def entrar_na_mesa(mesa_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")

    if current_user.balance < mesa.valor_minimo_aposta:
        raise HTTPException(status_code=400, detail="Saldo insuficiente para o buy-in.")

    jogador_existente = db.query(JogadorNaMesa).filter_by(user_id=current_user.id, mesa_id=mesa_id).first()
    if jogador_existente:
        raise HTTPException(status_code=400, detail="Você já está na mesa.")

    jogador_na_mesa = JogadorNaMesa(
        mesa_id=mesa.id,
        user_id=current_user.id,
        stack_inicial=mesa.valor_minimo_aposta,
        saldo_restante=mesa.valor_minimo_aposta,
        stack=mesa.valor_minimo_aposta,
    )

    db.add(jogador_na_mesa)
    current_user.balance -= mesa.valor_minimo_aposta
    db.commit()

    jogadores_na_mesa = db.query(JogadorNaMesa).filter_by(mesa_id=mesa.id).order_by(JogadorNaMesa.id).all()

    if len(jogadores_na_mesa) >= 2 and mesa.status == MesaStatus.aberta:
        return iniciar_partida(mesa, jogadores_na_mesa, db)
    else:
        return {"msg": f"Você entrou na mesa {mesa.nome} com sucesso! Aguardando mais jogadores para iniciar a partida."}





# Sair da mesa
@router.post("/{mesa_id}/jogadores/{jogador_id}/sair")
def sair_da_mesa(mesa_id: int, jogador_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if mesa is None:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")
    
    jogador = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id, user_id=current_user.id).first()
    if jogador is None:
        raise HTTPException(status_code=400, detail="Você não está nesta mesa.")

    current_user.balance += jogador.saldo_restante

    db.delete(jogador)
    db.commit()

    jogadores_restantes = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id).count()
    if jogadores_restantes < 2:
        mesa.status = MesaStatus.aberta
        mesa.aposta_atual = 0
        mesa.small_blind_pos = None
        mesa.big_blind_pos = None
        db.commit()

    return {"msg": f"Você saiu da mesa {mesa.nome} com sucesso! Saldo devolvido: R$ {jogador.saldo_restante:.2f}"}




@router.post("/{mesa_id}/showdown", tags=["Mesas"])
def finalizar_partida(mesa_id: int, db: Session = Depends(get_db)):
    mesa = get_mesa(db, mesa_id)
    jogadores = get_jogadores_da_mesa(mesa_id, db)
    controlador = ControladorDePartida(mesa, jogadores, db)
    return controlador.realizar_showdown()