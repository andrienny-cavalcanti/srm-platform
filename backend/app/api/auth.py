from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.core.security import verificar_senha, criar_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    senha: str


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email ou senha invalidos"
        )

    if not user.ativo:
        raise HTTPException(
            status_code=403,
            detail="Utilizador inativo"
        )

    if not verificar_senha(payload.senha, user.senha_hash):
        raise HTTPException(
            status_code=401,
            detail="Email ou senha invalidos"
        )

    token = criar_token({
        "sub": str(user.id),
        "company_id": user.company_id,
        "consultant_id": user.consultant_id,
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "role": user.role,
            "company_id": user.company_id,
            "consultant_id": user.consultant_id
        }
    }