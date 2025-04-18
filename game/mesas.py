from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Mesa, User, JogadorNaMesa, MesaStatus
from api.auth import get_current_user
from game.partida import iniciar_partida, get_mesa, get_jogadores_da_mesa, ControladorDePartida
import json



router = APIRouter(prefix="/mesas", tags=["Mesas"])



@router.get("/{mesa_id}/vez")
def vez_do_jogador(mesa_id: int, db: Session = Depends(get_db)):
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")
    
    return {"jogador_da_vez": mesa.jogador_da_vez_id}




@router.get("/{mesa_id}/jogadores")
def listar_jogadores_na_mesa(mesa_id: int, db: Session = Depends(get_db)):
    jogadores = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id).all()
    return [
        {
            "id": j.user.id,
            "username": j.user.username,
            "stack": j.stack,
            "saldo_restante": j.saldo_restante
        }
        for j in jogadores
    ]



# Entrar na mesa
@router.post("/{mesa_id}/entrar")
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
@router.post("/{mesa_id}/sair")
def sair_da_mesa(
    mesa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Buscar a mesa
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if mesa is None:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")
    
    # Buscar o jogador na mesa usando o usuário autenticado
    jogador = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id, user_id=current_user.id).first()
    if jogador is None:
        raise HTTPException(status_code=400, detail="Você não está nesta mesa.")

    # Devolver saldo para o jogador
    current_user.balance += jogador.saldo_restante

    # Remover jogador da mesa
    db.delete(jogador)
    db.commit()

    # Verificar se a mesa deve ser reaberta
    jogadores_restantes = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id).count()
    if jogadores_restantes < 2:
        mesa.status = MesaStatus.aberta
        mesa.aposta_atual = 0
        mesa.small_blind_pos = None
        mesa.big_blind_pos = None
        db.commit()

    return {
        "msg": f"Você saiu da mesa {mesa.nome} com sucesso! Saldo devolvido: R$ {jogador.saldo_restante:.2f}"
    }



@router.get("/{mesa_id}/cartas_comunitarias")
def get_cartas_comunitarias(mesa_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")

    response = {
        "flop": mesa.flop if mesa.estado_da_rodada in ["flop", "turn", "river"] else [],
        "turn": mesa.turn if mesa.estado_da_rodada in ["turn", "river"] and mesa.mostrar_turn else None,
        "river": mesa.river if mesa.estado_da_rodada == "river" and mesa.mostrar_river else None
    }
    return response




@router.get("/{mesa_id}/minhas_cartas")
def minhas_cartas(mesa_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    jogador = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id, user_id=current_user.id).first()
    if not jogador or not jogador.cartas:
        return []
    return json.loads(jogador.cartas)



@router.post("/{mesa_id}/avancar_rodada")
def avancar_rodada(mesa_id: int, db: Session = Depends(get_db)):
    mesa = get_mesa(db, mesa_id)

    if mesa.estado_da_rodada == "pre-flop":
        mesa.estado_da_rodada = "flop"
    elif mesa.estado_da_rodada == "flop":
        mesa.estado_da_rodada = "turn"
    elif mesa.estado_da_rodada == "turn":
        mesa.estado_da_rodada = "river"
    elif mesa.estado_da_rodada == "river":
        mesa.estado_da_rodada = "showdown"
    else:
        raise HTTPException(status_code=400, detail="Rodada já está no showdown")

    db.commit()
    return {"estado_atual": mesa.estado_da_rodada}


@router.post("/{mesa_id}/showdown", tags=["Mesas"])
def finalizar_partida(mesa_id: int, db: Session = Depends(get_db)):
    mesa = get_mesa(db, mesa_id)
    jogadores = get_jogadores_da_mesa(mesa_id, db)
    controlador = ControladorDePartida(mesa, jogadores, db)
    return controlador.realizar_showdown()