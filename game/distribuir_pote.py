from typing import List, Dict
from game.avaliador_maos import avaliar_mao


def criar_side_pots(jogadores: List[Dict]) -> List[Dict]:
    """
    Recebe jogadores com 'id' e 'aposta' (total que cada um apostou).
    Retorna uma lista de side pots: [{valor: float, participantes: [ids]}]
    """
    apostas = sorted(set(j['aposta'] for j in jogadores if j['aposta'] > 0))
    side_pots = []
    acumulado = 0

    for i, aposta in enumerate(apostas):
        pot_valor = (aposta - acumulado) * len([j for j in jogadores if j['aposta'] >= aposta])
        participantes = [j['id'] for j in jogadores if j['aposta'] >= aposta]
        side_pots.append({"valor": pot_valor, "participantes": participantes})
        acumulado = aposta

    return side_pots

def distribuir_pote(jogadores: List[Dict], vencedores: List[int]) -> Dict[int, float]:
    """
    jogadores -> [{'id': 1, 'aposta': 10}, ...]
    vencedores -> [1, 3]  (IDs dos vencedores do showdown)

    Retorna um dicionário com os ganhos por jogador: {1: 15.0, 3: 15.0}
    """
    ganhos = {j['id']: 0 for j in jogadores}
    side_pots = criar_side_pots(jogadores)

    for pot in side_pots:
        # Vencedores que têm direito a esse pote (estão no pote e venceram)
        vencedores_do_pot = [v for v in vencedores if v in pot['participantes']]
        if vencedores_do_pot:
            valor_por_vencedor = pot['valor'] / len(vencedores_do_pot)
            for v in vencedores_do_pot:
                ganhos[v] += valor_por_vencedor

    return ganhos
