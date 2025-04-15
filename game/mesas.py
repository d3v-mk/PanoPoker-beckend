from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Mesa, User, JogadorNaMesa, MesaStatus
from game.baralho import criar_baralho, embaralhar, distribuir_cartas, distribuir_comunidade
from api.auth import get_current_user

router = APIRouter(prefix="/mesas", tags=["Mesas"])


# Entrar na mesa

def entrar_na_mesa(mesa_id: int, jogador_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

    # Verifica se tem 2 jogadores na mesa, se tiver inicia a partida
    if len(jogadores_na_mesa) >= 2 and mesa.status == MesaStatus.aberta:
        mesa.status = MesaStatus.em_jogo

        # Define blinds fixos por mesa
        if mesa.valor_minimo_aposta == 0.30:
            small_blind_valor = 0.01
            big_blind_valor = 0.02
        elif mesa.valor_minimo_aposta == 2.00:
            small_blind_valor = 0.10
            big_blind_valor = 0.20
        elif mesa.valor_minimo_aposta == 10.00:
            small_blind_valor = 0.50
            big_blind_valor = 1.00
        else:
            small_blind_valor = round(mesa.valor_minimo_aposta * 0.1, 2)
            big_blind_valor = round(mesa.valor_minimo_aposta * 0.2, 2)

        # ROTACIONA blinds com base no big_blind anterior
        jogador_ids = [j.id for j in jogadores_na_mesa]
        if mesa.big_blind_pos in jogador_ids:
            big_index = jogador_ids.index(mesa.big_blind_pos)
            small_index = (big_index + 1) % len(jogadores_na_mesa)
            big_index = (small_index + 1) % len(jogadores_na_mesa)
        else:
            small_index = 0
            big_index = 1

        jogador_small = jogadores_na_mesa[small_index]
        jogador_big = jogadores_na_mesa[big_index]

        if jogador_small.stack < small_blind_valor or jogador_big.stack < big_blind_valor:
            raise HTTPException(status_code=400, detail="Um dos jogadores não tem saldo suficiente para pagar o blind.")

        # Deduz blinds dos stacks e atualiza aposta_atual
        jogador_small.stack -= small_blind_valor
        jogador_small.aposta_atual = small_blind_valor

        jogador_big.stack -= big_blind_valor
        jogador_big.aposta_atual = big_blind_valor

        # Atualiza mesa
        mesa.small_blind_pos = jogador_small.id
        mesa.big_blind_pos = jogador_big.id
        mesa.small_blind = small_blind_valor
        mesa.big_blind = big_blind_valor
        mesa.aposta_atual = big_blind_valor

        db.commit()

        baralho = criar_baralho()
        baralho = embaralhar(baralho)

        jogadores_ids = [j.user_id for j in jogadores_na_mesa]
        mao_jogadores, baralho = distribuir_cartas(jogadores_ids, baralho)
        flop, turn, river, baralho = distribuir_comunidade(baralho)

        return {
            "msg": f"Você entrou na mesa {mesa.nome} com sucesso! Partida iniciada com blinds definidos.",
            "small_blind": jogador_small.user_id,
            "big_blind": jogador_big.user_id,
            "aposta_atual_mesa": mesa.aposta_atual,
            "maos": [{"user_id": str(user_id), "cartas": cartas} for user_id, cartas in mao_jogadores.items()],
            "flop": list(flop),
            "turn": turn,
            "river": river
        }
        
    return {"msg": f"Você entrou na mesa {mesa.nome} com sucesso! Aguardando mais jogadores para iniciar a partida."}







# Sair da mesa
@router.post("/{mesa_id}/jogadores/{jogador_id}/sair")
def sair_da_mesa(mesa_id: int, jogador_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Verificar se a mesa existe
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if mesa is None:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")
    
    # Verificar se o jogador está na mesa
    jogador = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id, user_id=current_user.id).first()
    if jogador is None:
        raise HTTPException(status_code=400, detail="Você não está nesta mesa.")

    # Transferir o saldo restante de volta para o balance do usuário
    current_user.balance += jogador.saldo_restante

    # Remover o jogador da mesa
    db.delete(jogador)
    db.commit()

    # Verificar quantos jogadores restaram na mesa
    jogadores_restantes = db.query(JogadorNaMesa).filter_by(mesa_id=mesa_id).count()

    # Se restar 1 ou nenhum jogador, voltar o status da mesa pra 'aberta'
    if jogadores_restantes < 2:
        mesa.status = MesaStatus.aberta
        mesa.aposta_atual = 0
        mesa.small_blind_pos = None
        mesa.big_blind_pos = None
        db.commit()

    return {"msg": f"Você saiu da mesa {mesa.nome} com sucesso! Saldo devolvido: R$ {jogador.saldo_restante:.2f}"}



