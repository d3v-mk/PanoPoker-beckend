from itertools import combinations
from typing import List, Dict, Tuple
from .avaliador_maos import avaliar_mao

def determinar_vencedores(
    jogadores: List[Dict[str, List[str]]],
    cartas_comunitarias: List[str]
) -> List[int]:
    """
    Recebe:
        jogadores -> [{"id": 1, "cartas": ["A♠", "K♠"]}, ...]
        cartas_comunitarias -> ["Q♠", "J♠", "T♠", "2♦", "5♣"]
    Retorna:
        [id1, id2, ...]  (pode haver empate)
    """
    ranking_jogadores: List[Dict[str, Tuple[int, List[int]]]] = []

    for jogador in jogadores:
        cartas_total = jogador["cartas"] + cartas_comunitarias      # 7 cartas
        melhor_rank = (0, [])                                       # (força, tiebreakers)

        for mao in combinations(cartas_total, 5):
            rank = avaliar_mao(mao)
            if rank > melhor_rank:
                melhor_rank = rank

        ranking_jogadores.append({
            "jogador_id": jogador["id"],
            "melhor_mao": melhor_rank
        })

    ranking_ordenado = sorted(
        ranking_jogadores, key=lambda x: x["melhor_mao"], reverse=True
    )
    melhor_rank = ranking_ordenado[0]["melhor_mao"]

    # 🔍 Log dos rankings antes de determinar vencedores
    print("\n======= RANKING DOS JOGADORES =======")
    for r in ranking_ordenado:
        print(f"Jogador {r['jogador_id']} -> Mão: {r['melhor_mao']}")
    print("=====================================\n")

    vencedores = [
        r["jogador_id"] for r in ranking_ordenado if r["melhor_mao"] == melhor_rank
    ]
    return vencedores

if __name__ == "__main__":
    jogadores_exemplo = [
        {"id": 1, "cartas": ["A♠", "K♠"]},
        {"id": 2, "cartas": ["A♦", "A♥"]},
        {"id": 3, "cartas": ["9♣", "9♦"]},
    ]
    comunitarias = ["Q♠", "J♠", "T♠", "2♦", "5♣"]

    print("Vencedores:", determinar_vencedores(jogadores_exemplo, comunitarias))
