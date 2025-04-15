# api/mercadopago_ipn.py

import os
import requests
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import User

router = APIRouter(tags=["MercadoPago IPN"])

@router.api_route("/mercadopago/ipn")
async def ipn_listener(
    request: Request,
    db: Session = Depends(get_db),
    topic: str = Query(None),
    id: str = Query(None)
):
    try:
        if topic != "payment":
            return {"message": "Not a payment notification."}

        access_token = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
        url = f"https://api.mercadopago.com/v1/payments/{id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)
        payment_data = response.json()

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erro ao buscar dados do pagamento.")

        payment_status = payment_data.get("status")
        payer_email = payment_data.get("payer", {}).get("email")
        payment_value = payment_data.get("transaction_amount", 0)

        if payment_status == "approved":
            user = db.query(User).filter(User.email == payer_email).first()
            if user:
                user.balance += payment_value
                db.commit()
                return {
                    "message": f"Pagamento {id} aprovado e R${payment_value} adicionados ao saldo de {user.username}."
                }
            else:
                return {"message": f"Usuário com email {payer_email} não encontrado."}
        else:
            return {"message": f"Pagamento {id} não aprovado. Status: {payment_status}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar IPN: {str(e)}")
