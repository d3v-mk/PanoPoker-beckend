from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import random
import json
from db.database import get_db
from db.models import Mesa, JogadorNaMesa, MesaStatus
from game.baralho import criar_baralho, embaralhar, distribuir_cartas, distribuir_comunidade
from game.verificar_vencedor import determinar_vencedores
from game.distribuir_pote import distribuir_pote

router = APIRouter(prefix="/mesas", tags=["Mesas"])

def get_mesa(db: Session, mesa_id: int) -> Mesa:
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa não encontrada.")
    return mesa

def get_jogadores_da_mesa(mesa_id: int, db: Session):
    return db.query(JogadorNaMesa).filter(JogadorNaMesa.mesa_id == mesa_id).all()

def definir_blinds(mesa: Mesa, jogadores: list[JogadorNaMesa], db: Session):
    print(">>> DEFININDO BLINDS")

    if mesa.valor_minimo == 0.30:
        small_blind_valor = 0.01
        big_blind_valor = 0.02
    else:
        small_blind_valor = round(mesa.valor_minimo * 0.1, 2)
        big_blind_valor = round(mesa.valor_minimo * 0.2, 2)

    posicoes = list(range(len(jogadores)))
    small_blind_index = random.choice(posicoes)
    big_blind_index = (small_blind_index + 1) % len(jogadores)

    jogador_small = jogadores[small_blind_index]
    jogador_big = jogadores[big_blind_index]

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

    mesa.small_blind_pos = small_blind_index
    mesa.big_blind_pos = big_blind_index
    mesa.small_blind = small_blind_valor
    mesa.big_blind = big_blind_valor
    mesa.aposta_atual = big_blind_valor

    db.add(mesa)
    db.commit()
    db.refresh(mesa)

    print(">>> Blinds definidos com sucesso!")

def rotacionar_blinds(mesa: Mesa, jogadores: list[JogadorNaMesa]):
    jogador_ids = [j.id for j in jogadores]
    if mesa.big_blind_pos in jogador_ids:
        big_index = jogador_ids.index(mesa.big_blind_pos)
        small_index = (big_index + 1) % len(jogadores)
        big_index = (small_index + 1) % len(jogadores)
    else:
        small_index = 0
        big_index = 1
    return jogadores[small_index], jogadores[big_index]

def iniciar_partida(mesa: Mesa, jogadores_na_mesa: list[JogadorNaMesa], db: Session):
    mesa.status = MesaStatus.em_jogo
    definir_blinds(mesa, jogadores_na_mesa, db)

    small_blind_valor = mesa.small_blind
    big_blind_valor = mesa.big_blind

    jogador_small, jogador_big = rotacionar_blinds(mesa, jogadores_na_mesa)

    if jogador_small.stack < small_blind_valor or jogador_big.stack < big_blind_valor:
        raise HTTPException(status_code=400, detail="Um dos jogadores não tem saldo suficiente para pagar o blind.")

    mesa.small_blind_pos = jogador_small.id
    mesa.big_blind_pos = jogador_big.id
    mesa.small_blind = small_blind_valor
    mesa.big_blind = big_blind_valor
    mesa.aposta_atual = big_blind_valor

    db.commit()

    baralho = embaralhar(criar_baralho())
    jogadores_ids = [j.user_id for j in jogadores_na_mesa]
    mao_jogadores, baralho = distribuir_cartas(jogadores_ids, baralho)
    flop, turn, river, baralho = distribuir_comunidade(baralho)

    for jogador in jogadores_na_mesa:
        if jogador.user_id in mao_jogadores:
            jogador.cartas = json.dumps(mao_jogadores[jogador.user_id])
            db.add(jogador)

    db.commit()

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

class ControladorDePartida:
    def __init__(self, mesa: Mesa, jogadores: list[JogadorNaMesa], db: Session):
        self.mesa = mesa
        self.jogadores = jogadores
        self.db = db
        self.baralho = embaralhar(criar_baralho())
        self.community_cards = []
        self.rodada_atual = "pre-flop"
        self.pote = 0

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

        self.db.commit()

        print(f"🏆 Vencedor(es): {vencedores}")

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

        self.db.commit()

        print("🃏 Nova rodada pronta para começar!")

