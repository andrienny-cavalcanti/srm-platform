from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1)

class ChatResponse(BaseModel):
    reply: str
    intent: str
    lead_id: int | None = None

class ConsultantMessageRequest(BaseModel):
    content: str