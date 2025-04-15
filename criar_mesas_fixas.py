from db.database import SessionLocal
from db.models import Mesa, MesaStatus
import sys
import os

#python -m game.criar_mesas_fixas

db = SessionLocal()

# Verificar se as mesas já existem
if db.query(Mesa).count() == 0:
    mesas_fixas = [
        Mesa(
            id=1,
            nome="Mesa Bronze",
            status=MesaStatus.aberta,
            limite_jogadores=6,
            tipo_jogo="Texas Hold'em",
            valor_minimo=0.30,  # Adicionando o valor mínimo da mesa
            valor_minimo_aposta=0.30,
            small_blind=0.01,
            big_blind=0.02,
        ),
        Mesa(
            id=2,
            nome="Mesa Prata",
            status=MesaStatus.aberta,
            limite_jogadores=6,
            tipo_jogo="Texas Hold'em",
            valor_minimo=2.00,  # Adicionando o valor mínimo da mesa
            valor_minimo_aposta=2.00,
            small_blind=0.05,
            big_blind=0.10,
        ),
        Mesa(
            id=3,
            nome="Mesa Ouro",
            status=MesaStatus.aberta,
            limite_jogadores=6,
            tipo_jogo="Texas Hold'em",
            valor_minimo=10.00,  # Adicionando o valor mínimo da mesa
            valor_minimo_aposta=10.00,
            small_blind=0.25,
            big_blind=0.50,
        ),
    ]

    db.add_all(mesas_fixas)
    db.commit()
    print("Mesas fixas criadas com sucesso!")
else:
    print("As mesas já foram criadas anteriormente.")

db.close()
