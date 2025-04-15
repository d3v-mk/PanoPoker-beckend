import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from db.database import get_db
from db.models import User, Transaction
from api.auth import decode_access_token, get_current_user
from api.schemas import SaqueInput
from api.mp import criar_cobranca_pix

router = APIRouter(tags=["Saque"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

@router.post("/saque")
def sacar(
    saque_input: SaqueInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valor = saque_input.valor
    taxa_saque = 0.25
    valor_minimo = 10.0
    valor_maximo = 1000.0

    if valor < valor_minimo:
        raise HTTPException(status_code=400, detail=f"Valor mínimo para saque é R${valor_minimo}")
    if valor > valor_maximo:
        raise HTTPException(status_code=400, detail=f"Valor máximo por saque é R${valor_maximo}")

    valor_total = valor + taxa_saque

    if current_user.balance < valor_total:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo insuficiente. É necessário R${valor_total:.2f} (valor + taxa de R${taxa_saque:.2f})"
        )

    try:
        pagamento = criar_cobranca_pix(valor, current_user.username, current_user.email)
        print("Resposta completa do Mercado Pago:", pagamento)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar cobrança no Mercado Pago: {str(e)}")

    if 'point_of_interaction' not in pagamento:
        raise HTTPException(status_code=500, detail="Erro ao criar cobrança no Mercado Pago. 'point_of_interaction' não encontrado.")
    
    try:
        qr_code = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]
    except KeyError:
        raise HTTPException(status_code=500, detail="Erro ao acessar QR Code. Dados de transação incompletos.")

    current_user.balance -= valor_total
    db.commit()

    transacao = Transaction(
        user_id=current_user.id,
        tipo="saque",
        valor=valor,
        saldo_restante=current_user.balance
    )
    db.add(transacao)
    db.commit()

    return {
        "msg": f"Saque de R${valor:.2f} realizado com sucesso!",
        "taxa": taxa_saque,
        "total_descontado": valor_total,
        "new_balance": current_user.balance,
        "qr_code": qr_code
    }
