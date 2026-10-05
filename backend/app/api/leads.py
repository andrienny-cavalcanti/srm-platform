from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ( Lead, Consultant,User, LeadAssignmentHistory, LeadStatusHistory,   LeadStatusChangeRequest, )
from app.schemas.lead import ( LeadCreate, LeadOut, LeadStatusChangeRequestCreate, LeadStatusChangeRequestOut, )
from app.schemas.consultant import ConsultantCreate, ConsultantOut
from app.core.auth import obter_usuario_token


def exigir_admin(usuario):
    if usuario.get("role") != "ADM":
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem realizar esta operação."
        )

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=list[LeadOut])
def list_leads(
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
   company_id = usuario.get("company_id")
   query = db.query(Lead).filter(Lead.company_id == company_id)

   if usuario.get("role") == "CONSULTOR":
       query = query.filter(Lead.consultor_id == usuario.get("consultant_id"))

   return query.order_by(Lead.created_at.desc()).all()


@router.post("", response_model=LeadOut)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    company_id = usuario.get("company_id")

    dados = payload.model_dump()

    # =========================================================
    # REGRA DE CRIAÇÃO DO LEAD
    # =========================================================
    # CONSULTOR não pode criar um lead já atribuído
    # nem escolher diretamente o status.
    # =========================================================

    if usuario.get("role") == "CONSULTOR":
        dados["status"] = "NOVO"
        dados["consultor_id"] = None

    lead = Lead(
        **dados,
        company_id=company_id
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead
# =========================================================
# SOLICITAÇÃO DE ALTERAÇÃO DE STATUS
# =========================================================
# Consultores não alteram o status diretamente.
# Esta rota registra uma solicitação para análise do ADM.
# A criação da solicitação NÃO altera o status do lead.
# =========================================================

@router.post(
    "/{lead_id}/status-request",
    response_model=LeadStatusChangeRequestOut
)
def request_status_change(
    lead_id: int,
    payload: LeadStatusChangeRequestCreate,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    # Somente consultores utilizam este fluxo.
    # Administradores continuam podendo alterar o status diretamente.
    if usuario.get("role") != "CONSULTOR":
        raise HTTPException(
            status_code=403,
            detail="Apenas consultores podem enviar solicitações de alteração de status."
        )

    company_id = usuario.get("company_id")
    consultant_id = usuario.get("consultant_id")

    # Localiza o lead dentro da empresa do usuário.
    # Isso impede que um usuário acesse leads de outra empresa.
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
            detail="Lead não encontrado."
        )

    # O consultor só pode solicitar alteração para leads
    # que estejam atualmente atribuídos a ele.
    if lead.consultor_id != consultant_id:
        raise HTTPException(
            status_code=403,
            detail="Este lead não está atribuído a este consultor."
        )

    status_permitidos = [
        "NOVO",
        "EM_QUALIFICACAO",
        "PRONTO_PARA_CONSULTOR",
        "ATRIBUIDO_AO_CONSULTOR",
        "EM_CONTATO",
        "COTACAO_REALIZADA",
        "PROPOSTA_ENVIADA",
        "CONTRATADO",
        "SEM_RESPOSTA",
        "DADOS_INCOMPLETOS",
        "SEM_INTERESSE",
        "PERDIDO",
    ]

    # O status solicitado precisa pertencer ao conjunto
    # oficial de status utilizados pelo CRM.
    if payload.requested_status not in status_permitidos:
        raise HTTPException(
            status_code=400,
            detail="Status solicitado inválido."
        )

    # Não faz sentido solicitar uma alteração para o
    # mesmo status que o lead já possui.
    if payload.requested_status == lead.status:
        raise HTTPException(
            status_code=400,
            detail="O lead já possui este status."
        )

    # Impede múltiplas solicitações pendentes para o mesmo lead.
    # Isso evita que o ADM receba várias solicitações duplicadas.
    solicitacao_pendente = (
        db.query(LeadStatusChangeRequest)
        .filter(
            LeadStatusChangeRequest.lead_id == lead.id,
            LeadStatusChangeRequest.status == "PENDENTE"
        )
        .first()
    )

    if solicitacao_pendente:
        raise HTTPException(
            status_code=409,
            detail="Este lead já possui uma solicitação de alteração de status pendente."
        )

    # Registra o pedido sem alterar o status oficial do lead.
    solicitacao = LeadStatusChangeRequest(
        lead_id=lead.id,
        requested_by_user_id=int(usuario.get("sub")),
        old_status=lead.status,
        requested_status=payload.requested_status,
        reason=payload.reason,
        status="PENDENTE"
    )

    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)

    return solicitacao

# =========================================================
# LISTAGEM DE SOLICITAÇÕES DE ALTERAÇÃO DE STATUS
# =========================================================
# Somente administradores podem visualizar as solicitações
# pendentes de aprovação.
#
# A consulta é limitada à empresa do administrador para
# impedir acesso a solicitações de outras empresas.
# =========================================================

@router.get(
    "/status-requests",
    response_model=list[LeadStatusChangeRequestOut]
)
def list_status_change_requests(
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    # O fluxo de aprovação é exclusivo do administrador.
    exigir_admin(usuario)

    company_id = usuario.get("company_id")

    # Busca somente solicitações pendentes vinculadas a
    # leads pertencentes à empresa do administrador.
    solicitacoes = (
        db.query(LeadStatusChangeRequest)
        .join(
            Lead,
            Lead.id == LeadStatusChangeRequest.lead_id
        )
        .filter(
            Lead.company_id == company_id,
            LeadStatusChangeRequest.status == "PENDENTE"
        )
        .order_by(
            LeadStatusChangeRequest.created_at.asc()
        )
        .all()
    )

    return solicitacoes

# =========================================================
# APROVAÇÃO DE ALTERAÇÃO DE STATUS
# =========================================================
# Somente o ADM pode aprovar uma solicitação.
#
# A aprovação altera o status oficial do lead e cria o
# histórico correspondente na mesma transação.
# =========================================================

@router.post(
    "/status-requests/{request_id}/approve",
    response_model=LeadStatusChangeRequestOut
)
def approve_status_change_request(
    request_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    # Apenas administradores podem aprovar solicitações.
    exigir_admin(usuario)

    company_id = usuario.get("company_id")

    # Busca a solicitação junto com o lead para garantir que
    # ela pertence à empresa do administrador.
    solicitacao = (
        db.query(LeadStatusChangeRequest)
        .join(
            Lead,
            Lead.id == LeadStatusChangeRequest.lead_id
        )
        .filter(
            LeadStatusChangeRequest.id == request_id,
            Lead.company_id == company_id
        )
        .first()
    )

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação de alteração não encontrada."
        )

    # Uma solicitação só pode ser analisada uma vez.
    if solicitacao.status != "PENDENTE":
        raise HTTPException(
            status_code=409,
            detail="Esta solicitação já foi analisada."
        )

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == solicitacao.lead_id,
            Lead.company_id == company_id
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead relacionado à solicitação não encontrado."
        )

    # Guardamos o status real no momento da aprovação.
    # Isso protege contra uma alteração concorrente no lead
    # depois que a solicitação foi criada.
    status_anterior = lead.status

    # O histórico oficial registra a mudança efetivamente
    # realizada pelo administrador.
    if status_anterior != solicitacao.requested_status:
        historico_status = LeadStatusHistory(
            lead_id=lead.id,
            old_status=status_anterior,
            new_status=solicitacao.requested_status,
            changed_by_user_id=int(usuario.get("sub"))
        )

        db.add(historico_status)

        lead.status = solicitacao.requested_status

    # Registra quem analisou e quando a solicitação foi aprovada.
    solicitacao.status = "APROVADA"
    solicitacao.reviewed_by_user_id = int(usuario.get("sub"))
    solicitacao.reviewed_at = datetime.utcnow()

    # O histórico do lead e a aprovação são confirmados juntos.
    db.commit()
    db.refresh(solicitacao)

    return solicitacao

# =========================================================
# REJEIÇÃO DE ALTERAÇÃO DE STATUS
# =========================================================
# Somente o ADM pode rejeitar uma solicitação.
#
# A rejeição encerra a solicitação, mas NÃO altera o
# status oficial do lead.
# =========================================================

@router.post(
    "/status-requests/{request_id}/reject",
    response_model=LeadStatusChangeRequestOut
)
def reject_status_change_request(
    request_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    # Apenas administradores podem rejeitar solicitações.
    exigir_admin(usuario)

    company_id = usuario.get("company_id")

    # Busca a solicitação junto ao lead para garantir que
    # ela pertence à empresa do administrador.
    solicitacao = (
        db.query(LeadStatusChangeRequest)
        .join(
            Lead,
            Lead.id == LeadStatusChangeRequest.lead_id
        )
        .filter(
            LeadStatusChangeRequest.id == request_id,
            Lead.company_id == company_id
        )
        .first()
    )

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação de alteração não encontrada."
        )

    # Uma solicitação só pode ser analisada uma vez.
    if solicitacao.status != "PENDENTE":
        raise HTTPException(
            status_code=409,
            detail="Esta solicitação já foi analisada."
        )

    # A rejeição não altera o Lead.
    # Apenas registra a decisão administrativa.
    solicitacao.status = "REJEITADA"
    solicitacao.reviewed_by_user_id = int(usuario.get("sub"))
    solicitacao.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(solicitacao)

    return solicitacao

@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int,
    payload: LeadCreate,
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
            detail="Lead nao encontrado"
        )

    dados = payload.model_dump(exclude_unset=True)

# =========================================================
# PERMISSÃO DO CONSULTOR
# =========================================================

    if usuario.get("role") == "CONSULTOR":
        if lead.consultor_id != usuario.get("consultant_id"):
            raise HTTPException(
                status_code=403,
                detail="Este lead não está atribuído a este consultor."
            )

        if "status" in dados:
            raise HTTPException(
                status_code=403,
                detail="Consultores não podem alterar o status diretamente. Envie uma solicitação de alteração."
            )

# =========================================================
# HISTÓRICO DE STATUS
# =========================================================

    if "status" in dados:
        status_permitidos = [
            "NOVO",
            "EM_QUALIFICACAO",
            "PRONTO_PARA_CONSULTOR",
            "ATRIBUIDO_AO_CONSULTOR",
            "EM_CONTATO",
            "COTACAO_REALIZADA",
            "PROPOSTA_ENVIADA",
            "CONTRATADO",
            "SEM_RESPOSTA",
            "DADOS_INCOMPLETOS",
            "SEM_INTERESSE",
            "PERDIDO",
        ]

        if dados["status"] not in status_permitidos:
            raise HTTPException(
                status_code=400,
                detail="Status inválido."
            )

        status_anterior = lead.status
        status_novo = dados["status"]

        if status_anterior != status_novo:
            historico_status = LeadStatusHistory(
                lead_id=lead.id,
                old_status=status_anterior,
                new_status=status_novo,
                changed_by_user_id=int(usuario.get("sub"))
            )

            db.add(historico_status)

    # =========================================================
    # HISTÓRICO DE ATRIBUIÇÃO
    # =========================================================

    if "consultor_id" in dados:
        exigir_admin(usuario)

        consultor_anterior = lead.consultor_id
        consultor_novo = dados["consultor_id"]

        if consultor_anterior != consultor_novo:

            if consultor_anterior is None and consultor_novo is not None:
                acao = "ATRIBUIDO"

            elif consultor_anterior is not None and consultor_novo is None:
                acao = "REMOVIDO"

            else:
                acao = "TRANSFERIDO"

            historico = LeadAssignmentHistory(
                lead_id=lead.id,
                consultant_id=consultor_novo,
                changed_by_user_id=int(usuario.get("sub")),
                action=acao
            )

            db.add(historico)

    # =========================================================
    # ATUALIZAÇÃO DO LEAD
    # =========================================================

    for key, value in dados.items():
        setattr(lead, key, value)

    db.commit()
    db.refresh(lead)

    return lead

@router.get("/consultants/list")
def list_consultants(
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    company_id = usuario.get("company_id")

    consultants = (
        db.query(Consultant)
        .filter(
            Consultant.company_id == company_id,
            Consultant.ativo == 1
        )
        .order_by(Consultant.nome.asc())
        .all()
    )

    return consultants

@router.post("/consultants", response_model=ConsultantOut)
def create_consultant(
    payload: ConsultantCreate,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    exigir_admin(usuario)

    company_id = usuario.get("company_id")

    consultant = Consultant(
        nome=payload.nome,
        email=payload.email,
        telefone=payload.telefone,
        ativo=payload.ativo,
        company_id=company_id
    )

    db.add(consultant)
    db.commit()
    db.refresh(consultant)

    return consultant

@router.get("/consultants")
def list_all_consultants(
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    exigir_admin(usuario)

    company_id = usuario.get("company_id")

    consultants = (
        db.query(Consultant)
        .filter(Consultant.company_id == company_id)
        .order_by(Consultant.nome.asc())
        .all()
    )

    return [
        {
            "id": consultant.id,
            "nome": consultant.nome,
            "email": consultant.email,
            "telefone": consultant.telefone,
            "ativo": consultant.ativo,
        }
        for consultant in consultants
    ]

    return [
        {
            "id": consultant.id,
            "nome": consultant.nome,
            "email": consultant.email,
            "telefone": consultant.telefone,
        }
        for consultant in consultants
    ]

@router.get("/{lead_id}/assignment-history")
def get_assignment_history(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    company_id = usuario.get("company_id")

    if usuario.get("role") != "ADM":
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem consultar o histórico de atribuições."
        )

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
            detail="Lead nao encontrado"
        )

    history = (
        db.query(LeadAssignmentHistory)
        .filter(
            LeadAssignmentHistory.lead_id == lead_id
        )
        .order_by(
            LeadAssignmentHistory.created_at.desc()
        )
        .all()
    )

    resultado = []

    for item in history:
        consultor_nome = None
        usuario_nome = None

        if item.consultant_id:
            consultor = (
                db.query(Consultant)
                .filter(
                    Consultant.id == item.consultant_id
                )
                .first()
            )

            if consultor:
                consultor_nome = consultor.nome

        if item.changed_by_user_id:
            usuario_alteracao = (
                db.query(User)
                .filter(
                    User.id == item.changed_by_user_id
                )
                .first()
            )

            if usuario_alteracao:
                usuario_nome = usuario_alteracao.nome

        resultado.append(
            {
                "id": item.id,
                "lead_id": item.lead_id,
                "consultant_id": item.consultant_id,
                "consultant_name": consultor_nome,
                "changed_by_user_id": item.changed_by_user_id,
                "changed_by_user_name": usuario_nome,
                "action": item.action,
                "created_at": item.created_at,
            }
        )

    return resultado

@router.get("/{lead_id}/status-history")
def get_status_history(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(obter_usuario_token)
):
    company_id = usuario.get("company_id")

    if usuario.get("role") != "ADM":
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem consultar o histórico de status."
        )

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
            detail="Lead nao encontrado"
        )

    history = (
        db.query(LeadStatusHistory)
        .filter(
            LeadStatusHistory.lead_id == lead_id
        )
        .order_by(
            LeadStatusHistory.created_at.desc()
        )
        .all()
    )

    resultado = []

    for item in history:
        usuario_nome = None

        if item.changed_by_user_id:
            usuario_alteracao = (
                db.query(User)
                .filter(
                    User.id == item.changed_by_user_id
                )
                .first()
            )

            if usuario_alteracao:
                usuario_nome = usuario_alteracao.nome

        resultado.append(
            {
                "id": item.id,
                "lead_id": item.lead_id,
                "old_status": item.old_status,
                "new_status": item.new_status,
                "changed_by_user_id": item.changed_by_user_id,
                "changed_by_user_name": usuario_nome,
                "created_at": item.created_at,
            }
        )

    return resultado

@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
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
            detail="Lead nao encontrado"
        )

    return lead


