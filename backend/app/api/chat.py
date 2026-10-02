from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Company, Lead, Conversation, Message , User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConsultantMessageRequest
)
from app.core.auth import obter_usuario_token
from app.services.ai_service import (
    classify_intent,
    generate_reply,
    extract_lead_data
)
from app.services.lead_service import (
    get_or_create_conversation,
    create_lead,
    update_lead,
    save_message
)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    company = (
        db.query(Company)
        .filter(
            Company.slug == payload.company_slug,
            Company.ativo == 1
        )
        .first()
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada ou inativa"
        )
    
    # Recupera ou cria a conversa
    conversation = get_or_create_conversation(
        db,
        payload.session_id
    )

    # Salva mensagem do cliente
    save_message(
        db,
        conversation.id,
        "user",
        payload.message
    )

    # Identifica intenção
    intent = classify_intent(payload.message)

    # Recupera ou cria o lead
    lead = conversation.lead

    if lead is None:
        lead = create_lead(db, intent, company_id=company.id)

        conversation.lead_id = lead.id
        db.commit()
        db.refresh(conversation)

    # Extrai informações da mensagem
    extracted_data = extract_lead_data(payload.message)

    # Atualiza objetivo caso tenha sido identificado
    if intent != "informacao":
        extracted_data["objetivo"] = intent

    # Atualiza o lead com os dados encontrados
    if extracted_data:
        update_lead(
            db,
            lead,
            **extracted_data
        )

    # Dados atuais do lead
    lead_data = {
        "nome": lead.nome,
        "tipo_veiculo": lead.tipo_veiculo,
        "marca": lead.marca,
        "modelo": lead.modelo,
        "ano": lead.ano,
        "cidade": lead.cidade,
        "estado": lead.estado
    }

    # Verifica se a qualificação está completa
    required_fields = [
        lead.nome,
        lead.tipo_veiculo,
        lead.marca,
        lead.modelo,
        lead.ano,
        lead.cidade,
        lead.estado
    ]

    if all(required_fields):
        if lead.status == "EM_QUALIFICACAO":
            lead.status = "PRONTO_PARA_CONSULTOR"

        lead.nivel_interesse = "ALTO"
        db.commit()
        db.refresh(lead)

    # Gera próxima resposta
    reply = generate_reply(
        payload.message,
        intent,
        lead_data
    )

    # Salva resposta da IA
    save_message(
        db,
        conversation.id,
        "assistant",
        reply
    )

    return ChatResponse(
        reply=reply,
        intent=intent,
        lead_id=lead.id
    )


@router.get("/chat/leads/{lead_id}/messages")
def get_lead_messages(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    company_id = usuario.get("company_id")

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.company_id == company_id
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead não encontrado"
        )

    conversation = (
        db.query(Conversation)
        .filter_by(lead_id=lead_id)
        .order_by(Conversation.created_at.desc())
        .first()
    )

    if not conversation:
        return []

    messages = (
        db.query(Message)
        .filter_by(conversation_id=conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    resultado = []

    for message in messages:
        author_name = None

        if message.user_id:
            user = (
                db.query(User)
                .filter(
                    User.id == message.user_id,
                    User.company_id == company_id
                )
                .first()
            )

            if user:
                author_name = user.nome

        if message.role == "user":
            author_name = author_name or "Cliente"

        elif message.role == "assistant":
            author_name = author_name or "BEM MAIS-AI"

        elif message.role == "consultant":
            author_name = author_name or "Consultor"

        resultado.append({
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "user_id": message.user_id,
            "author_name": author_name,
            "created_at": message.created_at
        })

    return resultado
@router.post("/leads/{lead_id}/messages")
def send_consultant_message(
    lead_id: int,
    payload: ConsultantMessageRequest,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    company_id = usuario.get("company_id")
    user_id = int(usuario.get("sub"))
    role = usuario.get("role")

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.company_id == company_id
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead não encontrado"
        )

    if role == "CONSULTOR":
        consultant_id = usuario.get("consultant_id")

        if lead.consultor_id != consultant_id:
            raise HTTPException(
                status_code=403,
                detail="Este lead não está atribuído a este consultor."
            )

    if role not in ["ADM", "CONSULTOR"]:
        raise HTTPException(
            status_code=403,
            detail="Utilizador sem permissão para enviar mensagens."
        )

    conversation = (
        db.query(Conversation)
        .filter_by(lead_id=lead_id)
        .order_by(Conversation.created_at.desc())
        .first()
    )

    if not conversation:
        conversation = get_or_create_conversation(
            db,
            f"lead-{lead_id}"
        )
        conversation.lead_id = lead_id
        db.commit()
        db.refresh(conversation)

    message = save_message(
        db=db,
        conversation_id=conversation.id,
        role="consultant",
        content=payload.content,
        user_id=user_id
    )

    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "user_id": message.user_id,
        "created_at": message.created_at
    }