from pydantic import BaseModel

class LeadCreate(BaseModel):
    nome: str | None = None
    canal_origem: str = "chat_web"
    tipo_veiculo: str | None = None
    marca: str | None = None
    modelo: str | None = None
    ano: str | None = None
    cidade: str | None = None
    estado: str | None = None
    objetivo: str | None = None
    plano_interesse: str | None = None
    resumo: str | None = None
    nivel_interesse: str | None = None
    status: str = "NOVO"
    consultor_id: int | None = None

class LeadOut(LeadCreate):
    id: int

    class Config:
        from_attributes = True
class LeadStatusChangeRequestCreate(BaseModel):
    requested_status: str
    reason: str | None = None


class LeadStatusChangeRequestOut(BaseModel):
    id: int
    lead_id: int
    requested_by_user_id: int
    old_status: str
    requested_status: str
    reason: str | None = None
    status: str
    reviewed_by_user_id: int | None = None
    reviewed_at: str | None = None

    class Config:
        from_attributes = True
