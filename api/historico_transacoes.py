# api/historico_transacoes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Transaction, User
from api.auth import get_current_user

router = APIRouter(prefix="/historico", tags=["Transações"])

@router.get("/")
def historico(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transacoes = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    
    if not transacoes:
        raise HTTPException(status_code=404, detail="Nenhuma transação encontrada.")
    
    return {"transacoes": transacoes}
