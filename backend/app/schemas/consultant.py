from pydantic import BaseModel


class ConsultantCreate(BaseModel):
    nome: str
    email: str | None = None
    telefone: str | None = None
    ativo: int = 1


class ConsultantOut(ConsultantCreate):
    id: int
    company_id: int | None = None

    class Config:
        from_attributes = True
