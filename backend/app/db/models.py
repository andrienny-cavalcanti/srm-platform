from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    nome = Column(String(150), nullable=False)
    slug = Column(String(150), unique=True, nullable=False)
    ativo = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    nome = Column(String(120))
    canal_origem = Column(String(50), default="chat_web")
    tipo_veiculo = Column(String(80))
    marca = Column(String(80))
    modelo = Column(String(80))
    ano = Column(String(10))
    cidade = Column(String(100))
    estado = Column(String(50))
    objetivo = Column(String(50))
    plano_interesse = Column(String(120))
    resumo = Column(Text)
    nivel_interesse = Column(String(50))
    status = Column(String(50), default="NOVO")
    consultor_id = Column(Integer, ForeignKey("consultants.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="lead")

class Consultant(Base):
    __tablename__ = "consultants"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(180))
    telefone = Column(String(40))
    ativo = Column(Integer, default=1)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    session_id = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = relationship("Lead", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    consultant_id = Column(Integer, ForeignKey("consultants.id"), nullable=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="CONSULTOR")
    ativo = Column(Integer, nullable=False, default=1)
    aprovado = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LeadAssignmentHistory(Base):
    __tablename__ = "lead_assignment_history"

    id = Column(Integer, primary_key=True)

    lead_id = Column(
        Integer,
        ForeignKey("leads.id"),
        nullable=False
    )

    consultant_id = Column(
        Integer,
        ForeignKey("consultants.id"),
        nullable=True
    )

    changed_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    action = Column(
        String(30),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
class LeadStatusHistory(Base):
        __tablename__ = "lead_status_history"

        id = Column(Integer, primary_key=True)

        lead_id = Column(
            Integer,
            ForeignKey("leads.id"),
            nullable=False
        )

        old_status = Column(
            String(50),
            nullable=True
        )

        new_status = Column(
            String(50),
            nullable=False
        )

        changed_by_user_id = Column(
            Integer,
            ForeignKey("users.id"),
            nullable=True
        )

        created_at = Column(
            DateTime,
            default=datetime.utcnow
        )

class LeadStatusChangeRequest(Base):
    __tablename__ = "lead_status_change_requests"

    id = Column(Integer, primary_key=True)

    lead_id = Column(
        Integer,
        ForeignKey("leads.id"),
        nullable=False
    )

    requested_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    old_status = Column(
        String(50),
        nullable=False
    )

    requested_status = Column(
        String(50),
        nullable=False
    )

    reason = Column(
        Text,
        nullable=True
    )

    status = Column(
        String(30),
        nullable=False,
        default="PENDENTE"
    )

    reviewed_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    reviewed_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    
            