from db.database import SessionLocal
from db.models import Mesa, JogadorNaMesa, MesaStatus

# ID da mesa que você quer resetar
mesa_id = 1  # Altere para o ID da mesa desejada

# Criar uma nova sessão
db = SessionLocal()

# Buscar a mesa
mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()

if mesa:
    # Resetar status da mesa
    mesa.status = MesaStatus.aberta if hasattr(MesaStatus, "aberta") else "aberta"

    # Resetar valores de aposta
    mesa.aposta_atual = 0
    mesa.small_blind_pos = 1
    mesa.big_blind_pos = 2
    mesa.small_blind = 0.01
    mesa.big_blind = 0.02

    # Resetar os jogadores da mesa
    for jogador in mesa.jogadores:
        jogador.aposta_atual = 0
        jogador.stack = jogador.saldo_restante  # Retorna para o stack inicial da entrada
        jogador.status = "esperando"  # Se você estiver controlando status como 'ativo', 'esperando', etc.

    # Commitar as mudanças
    db.commit()

    print(f"Mesa {mesa_id} resetada com sucesso e pronta para nova partida!")

else:
    print(f"Mesa com ID {mesa_id} não encontrada.")

# Fechar a sessão
db.close()
