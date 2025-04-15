from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import User, Transaction
from api.auth import get_current_user
from api.mp import criar_cobranca_pix
from pydantic import BaseModel


router = APIRouter(tags=["Depositar"])

class DepositoInput(BaseModel):
    valor: float
    nome: str
    email: str


@router.post("/depositar")
def depositar(
    deposito: DepositoInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valor = deposito.valor
    nome = deposito.nome
    email = deposito.email
    
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Valor de depósito inválido.")

    pagamento = criar_cobranca_pix(valor, nome, email)

    current_user.balance += valor
    db.commit()

    transacao = Transaction(
        user_id=current_user.id,
        tipo="deposit",
        valor=valor,
        saldo_restante=current_user.balance,
    )
    db.add(transacao)
    db.commit()

    return {
        "msg": "Pagamento Pix gerado com sucesso",
        "qr_code_base64": pagamento["point_of_interaction"]["transaction_data"]["qr_code_base64"],
        "qr_code": pagamento["point_of_interaction"]["transaction_data"]["qr_code"],
        "new_balance": current_user.balance
    }

