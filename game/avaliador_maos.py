from itertools import combinations
from collections import Counter

# Valores em ordem de força (de menor para maior)
VALORES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
NAIPES = "♣♦♥♠"

# Ranking das mãos
RANKING = {
    "high_card": 1,
    "one_pair": 2,
    "two_pair": 3,
    "three_of_a_kind": 4,
    "straight": 5,
    "flush": 6,
    "full_house": 7,
    "four_of_a_kind": 8,
    "straight_flush": 9,
    "royal_flush": 10,
}

def valor_para_num(carta):
    return VALORES.index(carta[0])

def ordenar_mao(mao):
    return sorted(mao, key=lambda c: valor_para_num(c), reverse=True)

def is_sequencia(valores):
    valores = sorted(set(valores))
    if len(valores) < 5:
        return False
    for i in range(len(valores) - 4):
        if valores[i:i+5] == list(range(valores[i], valores[i]+5)):
            return True
    # Verifica sequencia A-2-3-4-5
    if set([12, 0, 1, 2, 3]).issubset(valores):
        return True
    return False

def avaliar_mao(mao):
    print(f"🕵️ Avaliando mão: {mao}")
    valores = []
    for c in mao:
        valor = c[:-1]  # tudo menos o naipe
        if valor not in VALORES:
            print(f"❌ Carta com valor inválido: {c} (extraído: {valor})")
            continue  # ignora carta inválida
        valores.append(VALORES.index(valor))
        
    naipes = [c[1] for c in mao]
    valor_count = Counter(valores)
    naipe_count = Counter(naipes)

    # Flush
    flush = None
    for naipe, count in naipe_count.items():
        if count >= 5:
            flush = [c for c in mao if c[1] == naipe]
            break

    # Straight
    straight = is_sequencia(valores)

    # Straight Flush / Royal Flush
    if flush:
        flush_vals = [VALORES.index(c[0]) for c in flush]
        if is_sequencia(flush_vals):
            if max(flush_vals) == 12:
                return (RANKING["royal_flush"], ordenar_mao(flush)[:5])
            else:
                return (RANKING["straight_flush"], ordenar_mao(flush)[:5])

    # Four of a kind
    for val, count in valor_count.items():
        if count == 4:
            kicker = max([v for v in valores if v != val])
            return (RANKING["four_of_a_kind"], [val]*4 + [kicker])

    # Full House
    trincas = [v for v, c in valor_count.items() if c == 3]
    pares = [v for v, c in valor_count.items() if c == 2]
    if trincas:
        if len(trincas) > 1:
            return (RANKING["full_house"], [max(trincas)]*3 + [min(trincas)]*2)
        elif pares:
            return (RANKING["full_house"], [trincas[0]]*3 + [max(pares)]*2)

    # Flush
    if flush:
        return (RANKING["flush"], [VALORES.index(c[0]) for c in ordenar_mao(flush)[:5]])

    # Straight
    if straight:
        return (RANKING["straight"], sorted(set(valores), reverse=True)[:5])

    # Trinca
    if trincas:
        kickers = sorted([v for v in valores if v != trincas[0]], reverse=True)[:2]
        return (RANKING["three_of_a_kind"], [trincas[0]]*3 + kickers)

    # Dois pares
    if len(pares) >= 2:
        top_pars = sorted(pares, reverse=True)[:2]
        kicker = max([v for v in valores if v not in top_pars])
        return (RANKING["two_pair"], top_pars*2 + [kicker])

    # Um par
    if len(pares) == 1:
        kicker = sorted([v for v in valores if v != pares[0]], reverse=True)[:3]
        return (RANKING["one_pair"], [pares[0]]*2 + kicker)

    # Carta alta
    return (RANKING["high_card"], sorted(valores, reverse=True)[:5])
