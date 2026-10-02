from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from jose import jwt

from .config import JWT_SECRET_KEY

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

password_hash = PasswordHash.recommended()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return password_hash.verify(senha, senha_hash)


def criar_token(data: dict) -> str:
    payload = data.copy()
    expiracao = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expiracao})
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
