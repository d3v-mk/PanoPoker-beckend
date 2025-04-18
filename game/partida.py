from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import random
import json
from db.database import get_db
from db.models import Mesa, JogadorNaMesa, MesaStatus
from game.baralho import criar_baralho, embaralhar, distribuir_cartas, distribuir_comunidade
from game.verificar_vencedor import determinar_vencedores
from game.distribuir_pote import distribuir_pote
from datetime import datetime

router = APIRouter(prefix="/mesas", tags=["Mesas"])

def get_mesa(db: Session, mesa_id: int) -> Mesa:
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")
    return mesa

def get_jogadores_da_mesa(mesa_id: int, db: Session):
    return db.query(JogadorNaMesa).filter(JogadorNaMesa.mesa_id == mesa_id).all()




def definir_blinds(mesa: Mesa, jogadores: list[JogadorNaMesa], db: Session):
    print(">>> DEFININDO BLINDS ROTATIVOS")

    if mesa.valor_minimo == 0.30:
        small_blind_valor = 0.01
        big_blind_valor = 0.02
    else:
        small_blind_valor = round(mesa.valor_minimo * 0.1, 2)
        big_blind_valor = round(mesa.valor_minimo * 0.2, 2)

    jogadores_ordenados = sorted(jogadores, key=lambda j: j.id)
    ids = [j.id for j in jogadores_ordenados]

    if mesa.small_blind_pos is None:
        # Primeira rodada
        small_index = 0
        big_index = 1 if len(jogadores) > 1 else 0
    else:
        last_sb_index = ids.index(mesa.small_blind_pos)
        small_index = (last_sb_index + 1) % len(jogadores)
        big_index = (small_index + 1) % len(jogadores)

    jogador_small = jogadores_ordenados[small_index]
    jogador_big = jogadores_ordenados[big_index]

    if jogador_small.stack < small_blind_valor:
        raise HTTPException(status_code=400, detail="Small blind sem stack suficiente")
    if jogador_big.stack < big_blind_valor:
        raise HTTPException(status_code=400, detail="Big blind sem stack suficiente")

    jogador_small.stack -= small_blind_valor
    jogador_small.aposta_atual = small_blind_valor

    jogador_big.stack -= big_blind_valor
    jogador_big.aposta_atual = big_blind_valor

    db.add(jogador_small)
    db.add(jogador_big)

    mesa.small_blind_pos = jogador_small.id
    mesa.big_blind_pos = jogador_big.id
    mesa.small_blind = small_blind_valor
    mesa.big_blind = big_blind_valor
    mesa.aposta_atual = big_blind_valor

    db.add(mesa)
    db.commit()
    db.refresh(mesa)

    print(f">>> SB: {jogador_small.user_id} | BB: {jogador_big.user_id} | Aposta atual: {mesa.aposta_atual}")





def atualizar_vez(mesa: Mesa, jogadores: list[JogadorNaMesa], db: Session):
    jogadores_ativos = [j for j in jogadores if not j.foldado and j.stack > 0]

    if len(jogadores_ativos) <= 1:
        mesa.jogador_da_vez_id = None  # Ninguém mais na rodada
        db.add(mesa)
        db.commit()
        return

    jogadores_ordenados = sorted(jogadores, key=lambda j: j.id)
    atual = next((i for i, j in enumerate(jogadores_ordenados) if j.user_id == mesa.jogador_da_vez_id), -1)

    for offset in range(1, len(jogadores_ordenados)):
        proximo = (atual + offset) % len(jogadores_ordenados)
        if not jogadores_ordenados[proximo].foldado and jogadores_ordenados[proximo].stack > 0:
            mesa.jogador_da_vez_id = jogadores_ordenados[proximo].user_id
            db.add(mesa)
            db.commit()
            print(f"🔁 Próxima vez é do jogador {mesa.jogador_da_vez_id}")
            return




def iniciar_partida(mesa: Mesa, jogadores_na_mesa: list[JogadorNaMesa], db: Session):
    mesa.status = MesaStatus.em_jogo

    # Agora já define blinds e aplica apostas corretas com rotação
    definir_blinds(mesa, jogadores_na_mesa, db)

    mesa.estado_da_rodada = "pre-flop"

    # Baralho e distribuição
    baralho = embaralhar(criar_baralho())
    jogadores_ids = [j.user_id for j in jogadores_na_mesa]
    mao_jogadores, baralho = distribuir_cartas(jogadores_ids, baralho)
    flop, turn, river, baralho = distribuir_comunidade(baralho)

    mesa.flop = flop
    mesa.turn = turn
    mesa.river = river

    # 🔁 Definir o jogador da vez corretamente (após o big blind e ativo)
    jogadores_ordenados = sorted(jogadores_na_mesa, key=lambda j: j.id)
    ids_ordenados = [j.id for j in jogadores_ordenados]

    if mesa.big_blind_pos in ids_ordenados:
        big_index = ids_ordenados.index(mesa.big_blind_pos)

        for offset in range(1, len(jogadores_ordenados)):
            idx = (big_index + offset) % len(jogadores_ordenados)
            jogador = jogadores_ordenados[idx]
            if not jogador.foldado and jogador.stack > 0:
                mesa.jogador_da_vez_id = jogador.user_id
                break
    else:
        mesa.jogador_da_vez_id = jogadores_ordenados[0].user_id  # fallback

    db.add(mesa)

    for jogador in jogadores_na_mesa:
        if jogador.user_id in mao_jogadores:
            jogador.cartas = json.dumps(mao_jogadores[jogador.user_id])
            db.add(jogador)

    db.commit()

    return {
        "msg": f"Você entrou na mesa {mesa.nome} com sucesso! Partida iniciada com blinds definidos.",
        "small_blind": mesa.small_blind_pos,
        "big_blind": mesa.big_blind_pos,
        "jogador_da_vez": mesa.jogador_da_vez_id,
        "aposta_atual_mesa": mesa.aposta_atual,
        "estado_da_rodada": mesa.estado_da_rodada,
        "maos": [{"user_id": str(user_id), "cartas": cartas} for user_id, cartas in mao_jogadores.items()],
        "flop": flop,
        "turn": turn,
        "river": river
    }



class ControladorDePartida:
    def __init__(self, mesa: Mesa, jogadores: list[JogadorNaMesa], db: Session):
        self.mesa = mesa
        self.jogadores = jogadores
        self.db = db
        self.baralho = embaralhar(criar_baralho())
        self.community_cards = []
        self.rodada_atual = "pre-flop"
        self.pote = 0



    def verificar_proxima_etapa(self):
        from datetime import datetime

        self.jogadores = self.db.query(JogadorNaMesa).filter_by(mesa_id=self.mesa.id).all()
        jogadores_ativos = [j for j in self.jogadores if not j.foldado and j.stack >= 0]

        if len(jogadores_ativos) <= 1:
            return

        print("\n🧠 DEBUG ESTADO DOS JOGADORES -", datetime.now())
        for j in jogadores_ativos:
            print(f"Jogador {j.user_id} | Foldado: {j.foldado} | Stack: {j.stack} | Aposta Atual: {j.aposta_atual} | Já Agiu: {j.rodada_ja_agiu}")
        print("--------------------------------------------------")

        def iguais(valores):
            return all(abs(v - valores[0]) < 0.001 for v in valores)

        apostas = [j.aposta_atual for j in jogadores_ativos]
        if not iguais(apostas):
            return

        if not all(j.rodada_ja_agiu for j in jogadores_ativos):
            return

        if self.mesa.estado_da_rodada == "pre-flop":
            self.mesa.estado_da_rodada = "flop"
            print("🌟 Estado da rodada mudou para FLOP")
        elif self.mesa.estado_da_rodada == "flop":
            self.mesa.estado_da_rodada = "turn"
            self.mesa.mostrar_turn = True
            print("👉 Turn revelado")
        elif self.mesa.estado_da_rodada == "turn":
            self.mesa.estado_da_rodada = "river"
            self.mesa.mostrar_river = True
            print("👉 River revelado")
        elif self.mesa.estado_da_rodada == "river":
            print("✅ Todas as rodadas finalizadas. Showdown em breve.")
            self.mesa.jogador_da_vez_id = None
            self.db.add(self.mesa)
            self.db.commit()
            self.realizar_showdown()
            return

        for j in self.jogadores:
            j.rodada_ja_agiu = False
            self.db.add(j)

        self.db.add(self.mesa)
        self.db.commit()

        # Só define nova vez se ainda não for showdown
        if self.mesa.estado_da_rodada in ["flop", "turn", "river"]:
            ativos = [j for j in self.jogadores if not j.foldado and j.stack > 0]
            if ativos:
                self.mesa.jogador_da_vez_id = ativos[0].user_id
                self.db.add(self.mesa)
                self.db.commit()
                print(f"🎯 Nova rodada: vez do jogador {self.mesa.jogador_da_vez_id}")







    def avancar_vez(self):
        jogadores_ativos = [j for j in self.jogadores if not j.foldado and j.stack > 0]

        if not jogadores_ativos:
            self.mesa.jogador_da_vez_id = None
        else:
            ids = [j.user_id for j in jogadores_ativos]

            if self.mesa.jogador_da_vez_id not in ids:
                # Se o jogador atual não estiver mais ativo, começa do primeiro
                self.mesa.jogador_da_vez_id = ids[0]
            else:
                index_atual = ids.index(self.mesa.jogador_da_vez_id)
                proximo_index = (index_atual + 1) % len(ids)
                self.mesa.jogador_da_vez_id = ids[proximo_index]

        self.db.add(self.mesa)
        self.db.commit()



    def jogadores_ativos(self):
        return [j for j in self.jogadores if not j.foldado and j.stack >= 0]

    def executar_rodada_apostas(self):
        print(f"⚙️ Executando apostas da rodada {self.rodada_atual}")
        for jogador in self.jogadores_ativos():
            if jogador.stack > 0:
                print(f"Jogador {jogador.user_id} ainda está na mão.")

    def verificar_fim_por_fold(self):
        return len(self.jogadores_ativos()) == 1

    def encerrar_partida_por_fold(self):
        vencedor = self.jogadores_ativos()[0]
        vencedor.stack += self.pote
        print(f"🏆 Vitória por fold! Jogador {vencedor.user_id} leva o pote de R${self.pote:.2f}")
        return {
            "vencedores": [vencedor.user_id],
            "pote": self.pote,
            "motivo": "fold"
        }

    def realizar_showdown(self):
        print("💥 Showdown!")

        # 🔐 Garante que community_cards foram geradas
        if not self.community_cards:
            print("⚠️ Cartas comunitárias estavam vazias. Gerando agora...")
            flop, turn, river, self.baralho = distribuir_comunidade(self.baralho)
            self.community_cards = list(flop) + [turn, river]
            print("Cartas comunitárias geradas no showdown:", self.community_cards)

        print("Cartas comunitárias:", self.community_cards)

        jogadores = self.jogadores_ativos()

        if len(jogadores) == 0:
            return {"msg": "Erro: nenhum jogador restante."}

        jogadores_info = []
        for j in jogadores:
            try:
                if not j.cartas:
                    raise ValueError("Cartas vazias")
                cartas = json.loads(j.cartas)
                print(f"Jogador {j.user_id} -> cartas carregadas: {cartas}")
            except Exception as e:
                print(f"[ERRO] Jogador {j.user_id} -> cartas inválidas: {j.cartas} | Erro: {e}")
                cartas = []

            jogadores_info.append({
                "id": j.user_id,
                "cartas": cartas,
                "aposta": j.aposta_atual
            })

        vencedores = determinar_vencedores(jogadores_info, self.community_cards)
        ganhos = distribuir_pote(jogadores_info, vencedores)

        for jogador in jogadores:
            ganho = ganhos.get(jogador.user_id, 0)
            jogador.stack += ganho
            jogador.saldo_restante = jogador.stack
            jogador.aposta_atual = 0
            self.db.add(jogador)

        self.db.add(self.mesa)  # ✅ Garante que o estado da mesa seja salvo
        self.db.commit()

        print(f"🏆 Vencedor(es): {vencedores}")
        print("✅ Fim do showdown. Pote distribuído e nova rodada será iniciada.")

        # Inicia nova rodada automaticamente
        self.nova_rodada()

        return {
            "vencedores": vencedores,
            "ganhos": ganhos,
            "cartas_comunitarias": self.community_cards,
            "maos": [
                {
                    "jogador_id": j["id"],
                    "mao": j["cartas"],
                    "mao_rank": determinar_vencedores([j], self.community_cards)[0] if j["id"] in vencedores else None
                } for j in jogadores_info
            ]
        }

    

    def nova_rodada(self):
        print("🔄 Iniciando nova rodada!")

        # Resetar jogadores
        for jogador in self.jogadores:
            jogador.aposta_atual = 0
            jogador.foldado = False
            jogador.rodada_ja_agiu = False
            jogador.cartas = json.dumps([])
            self.db.add(jogador)

        self.db.commit()

        # Redefinir baralho e community cards
        self.baralho = embaralhar(criar_baralho())
        self.community_cards = []
        self.pote = 0

        # Rotaciona blinds
        definir_blinds(self.mesa, self.jogadores, self.db)

        # Distribui novas cartas aos jogadores
        jogadores_ids = [j.user_id for j in self.jogadores]
        mao_jogadores, self.baralho = distribuir_cartas(jogadores_ids, self.baralho)

        for jogador in self.jogadores:
            if jogador.user_id in mao_jogadores:
                jogador.cartas = json.dumps(mao_jogadores[jogador.user_id])
                self.db.add(jogador)

        # 🃏 Distribuir flop, turn e river
        flop, turn, river, self.baralho = distribuir_comunidade(self.baralho)
        print("FLOP, TURN E RIVER:", flop, turn, river)
        self.community_cards = list(flop) + [turn, river]
        print("Community cards set:", self.community_cards)

        # ⚠️ ESSENCIAL: Resetar os estados de exibição
        self.mesa.mostrar_turn = False
        self.mesa.mostrar_river = False
        self.db.add(self.mesa)

        self.db.commit()

        print("🃏 Nova rodada pronta para começar!")


