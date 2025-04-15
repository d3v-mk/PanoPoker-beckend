from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Mesa, JogadorNaMesa
from typing import List
from api.schemas import MesaBase

router = APIRouter(prefix="/lobby", tags=["Lobby"])


# ✅ Nome de função único
@router.get("/mesas", response_model=List[MesaBase])
def listar_todas_mesas_lobby(db: Session = Depends(get_db)):
    mesas = db.query(Mesa).all()

    mesas_com_jogadores = [
        {
            "id": mesa.id,
            "nome": mesa.nome,
            "status": mesa.status.value if hasattr(mesa.status, "value") else mesa.status,
            "jogadores": db.query(JogadorNaMesa).filter(JogadorNaMesa.mesa_id == mesa.id).count(),
        }
        for mesa in mesas
    ]

    return mesas_com_jogadores

@router.get("/disponiveis")
def listar_mesas_disponiveis_para_entrada(db: Session = Depends(get_db)):
    mesas = db.query(Mesa).all()
    mesas_disponiveis = []

    for mesa in mesas:
        qtd_jogadores = db.query(JogadorNaMesa).filter(JogadorNaMesa.mesa_id == mesa.id).count()
        if mesa.status == "aberta" and qtd_jogadores < mesa.limite_jogadores:
            mesas_disponiveis.append({
                "id": mesa.id,
                "status": mesa.status,
                "limite_jogadores": mesa.limite_jogadores,
                "jogadores_atuais": qtd_jogadores,
                "tipo_jogo": mesa.tipo_jogo,
                "valor_minimo_aposta": mesa.valor_minimo_aposta
            })

    return mesas_disponiveis

