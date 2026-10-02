from sqlalchemy.orm import Session
from app.db.models import Lead, Conversation, Message


def get_or_create_conversation(db: Session, session_id: str):
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()

    if not conversation:
        conversation = Conversation(session_id=session_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    return conversation


def create_lead(
    db: Session,
    intent: str,
    canal="chat_web",
    company_id: int | None = None
):
    lead = Lead(
        company_id=company_id,
        canal_origem=canal,
        objetivo=intent,
        status="EM_QUALIFICACAO"
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead


def update_lead(db: Session, lead: Lead, **data):
    """
    Atualiza somente os campos recebidos.
    Campos vazios ou None são ignorados.
    """

    for field, value in data.items():
        if value is not None and value != "":
            if hasattr(lead, field):
                setattr(lead, field, value)

    db.commit()
    db.refresh(lead)

    return lead


def save_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    user_id: int | None = None
):
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        user_id=user_id
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message