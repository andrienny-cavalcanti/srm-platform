import { useEffect, useState } from "react";
import "./App.css";

const TOKEN_KEY = "bem_mais_ai_token";
const USER_KEY = "bem_mais_ai_user";

const API_URL = "http://localhost:8000";

const STATUS_OPTIONS = [
  ["NOVO", "Novo"],
  ["EM_QUALIFICACAO", "Em qualificação"],
  ["PRONTO_PARA_CONSULTOR", "Pronto para consultor"],
  ["ATRIBUIDO_AO_CONSULTOR", "Atribuído ao consultor"],
  ["EM_CONTATO", "Em contato"],
  ["COTACAO_REALIZADA", "Cotação realizada"],
  ["PROPOSTA_ENVIADA", "Proposta enviada"],
  ["CONTRATADO", "Contratado"],
  ["SEM_RESPOSTA", "Sem resposta"],
  ["DADOS_INCOMPLETOS", "Dados incompletos"],
  ["SEM_INTERESSE", "Sem interesse"],
  ["PERDIDO", "Perdido"],
];

function App() {
  const [leads, setLeads] = useState([]);
  const [consultants, setConsultants] = useState([]);
  const [selectedLead, setSelectedLead] = useState(null);
  const [assignmentHistory, setAssignmentHistory] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState("");
  const [savingStatus, setSavingStatus] = useState(false);

  const [token, setToken] = useState("");
  const [showLeadDetails, setShowLeadDetails] = useState(false);

  const [statusHistory, setStatusHistory] = useState([]);
  const [consultantMessage, setConsultantMessage] = useState("");
  // =========================================================
// STATUS DISPONÍVEIS PARA SOLICITAÇÃO
// =========================================================
// Mantemos a mesma lista oficial utilizada pelo sistema.
// O backend continuará sendo responsável pela validação final.
// =========================================================
const statusDisponiveisParaSolicitacao = [
  { value: "NOVO", label: "Novo" },
  { value: "EM_QUALIFICACAO", label: "Em análise" },
  {
    value: "PRONTO_PARA_CONSULTOR",
    label: "Pronto para consultor",
  },
  {
    value: "ATRIBUIDO_AO_CONSULTOR",
    label: "Atribuído ao consultor",
  },
  { value: "EM_CONTATO", label: "Em contato" },
  {
    value: "COTACAO_REALIZADA",
    label: "Cotação realizada",
  },
  {
    value: "PROPOSTA_ENVIADA",
    label: "Proposta enviada",
  },
  { value: "CONTRATADO", label: "Contratado" },
  { value: "SEM_RESPOSTA", label: "Sem resposta" },
  { value: "DADOS_INCOMPLETOS", label: "Dados incompletos" },
  { value: "SEM_INTERESSE", label: "Sem interesse" },
  { value: "PERDIDO", label: "Perdido" },
];

  // =========================================================
  // ESTADOS DA SOLICITAÇÃO DE ALTERAÇÃO DE STATUS
  // =========================================================
  // O consultor não altera o status diretamente.
  // Estes estados controlarão o formulário de solicitação.
  // =========================================================

  const [requestedStatus, setRequestedStatus] = useState("");
  const [requestReason, setRequestReason] = useState("");
  const [savingStatusRequest, setSavingStatusRequest] = useState(false);;

  const [usuario, setUsuario] = useState(() => {
  const salvo = localStorage.getItem(USER_KEY);
  return salvo ? JSON.parse(salvo) : null;
});
const [activePage, setActivePage] = useState("dashboard");

  async function fazerLogin(email, senha) {
  const response = await fetch(
    `${API_URL}/api/auth/login`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        senha,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Email ou senha inválidos.");
  }

  const data = await response.json();

  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));

  setToken(data.access_token);
  setUsuario(data.user);

  return data;
}

  async function carregarLeads() {
  try {
    setLoading(true);
    setError("");

    const response = await fetch(`${API_URL}/api/leads`, {
  headers: {
    Authorization: `Bearer ${token}`,
  },
});

   if (!response.ok) {
    const erro = await response.text();
    throw new Error(
      `Erro ao carregar leads: ${response.status} - ${erro}`
  );
}

    const data = await response.json();
    setLeads(Array.isArray(data) ? data : []);

    const consultantsResponse = await fetch(
  `${API_URL}/api/leads/consultants/list`,
  {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }
);

    if (!consultantsResponse.ok) {
      throw new Error("Não foi possível carregar os consultores.");
    }

    const consultantsData = await consultantsResponse.json();
    setConsultants(
     Array.isArray(consultantsData) ? consultantsData : []
    );
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

  async function abrirLead(leadId) {
  try {
    setError("");
    setLoadingMessages(true);
    setMessages([]);

    const headers = {
      Authorization: `Bearer ${token}`,
    };

   const requests = [
  fetch(`${API_URL}/api/leads/${leadId}`, {
    headers,
  }),
  fetch(`${API_URL}/api/chat/leads/${leadId}/messages`, {
    headers,
  }),
];

if (usuario?.role === "ADM") {
  requests.push(
    fetch(`${API_URL}/api/leads/${leadId}/assignment-history`, {
      headers,
    })
  );
}

const responses = await Promise.all(requests);

const leadResponse = responses[0];
const messagesResponse = responses[1];
const historyResponse = responses[2];

    if (!leadResponse.ok) {
      throw new Error("Não foi possível carregar o lead.");
    }

    if (!messagesResponse.ok) {
      throw new Error("Não foi possível carregar o histórico.");
    }

    if (usuario?.role === "ADM" && !historyResponse.ok) {
      throw new Error("Não foi possível carregar o histórico de atribuições.");
    }

    const leadData = await leadResponse.json();
    const messagesData = await messagesResponse.json();
    const historyData =
      usuario?.role === "ADM"
        ? await historyResponse.json()
        : [];

    setSelectedLead(leadData);
    setMessages(messagesData);
    setAssignmentHistory(historyData);
  } catch (err) {
    setError(err.message);
  } finally {
    setLoadingMessages(false);
  }
}
  async function enviarMensagemConsultor() {
  if (!consultantMessage.trim() || !selectedLead) {
    return;
  }

  try {
    setError("");

    const response = await fetch(
      `${API_URL}/api/leads/${selectedLead.id}/messages`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: consultantMessage.trim(),
        }),
      }
    );

    if (!response.ok) {
      const data = await response.json();
      throw new Error(
        data.detail || "Não foi possível enviar a mensagem."
      );
    }

    setConsultantMessage("");

    await abrirLead(selectedLead.id);
  } catch (err) {
    setError(err.message);
  }
}

  async function alterarStatus(novoStatus) {
    if (!selectedLead) {
      return;
    }

    try {
      setSavingStatus(true);
      setError("");

      const response = await fetch(
        `${API_URL}/api/leads/${selectedLead.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
             Authorization: `Bearer ${token}`,
},
          body: JSON.stringify({
            status: novoStatus,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Não foi possível atualizar o status.");
      }

      const updatedLead = await response.json();

      setSelectedLead(updatedLead);

      setLeads((currentLeads) =>
        currentLeads.map((lead) =>
          lead.id === updatedLead.id ? updatedLead : lead
        )
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingStatus(false);
    }
  }

  // =========================================================
  // SOLICITAÇÃO DE ALTERAÇÃO DE STATUS
  // =========================================================
  // Consultores não alteram o status oficial diretamente.
  // Esta função envia uma solicitação para análise do ADM.
  //
  // IMPORTANTE:
  // A criação da solicitação NÃO altera o status do lead.
  // O status só será alterado após aprovação do administrador.
  // =========================================================

  async function solicitarAlteracaoStatus() {
    if (!selectedLead || !requestedStatus) {
      return;
    }

    try {
      setSavingStatusRequest(true);
      setError("");

      const response = await fetch(
        `${API_URL}/api/leads/${selectedLead.id}/status-request`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            requested_status: requestedStatus,
            reason: requestReason.trim() || null,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Não foi possível enviar a solicitação de alteração."
        );
      }

      // Limpa o formulário depois que a solicitação foi registrada.
      setRequestedStatus("");
      setRequestReason("");

      setError(
        "Solicitação enviada para análise do administrador."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingStatusRequest(false);
    }
  }



  async function alterarConsultor(novoConsultorId) {
  if (!selectedLead) return;

  try {
    setError("");

    const response = await fetch(
      `${API_URL}/api/leads/${selectedLead.id}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
           Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          consultor_id: novoConsultorId
            ? Number(novoConsultorId)
            : null,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(
        "Não foi possível atualizar o consultor."
      );
    }

    const updatedLead = await response.json();

    setSelectedLead(updatedLead);

    setLeads((currentLeads) =>
      currentLeads.map((lead) =>
        lead.id === updatedLead.id
          ? updatedLead
          : lead
      )
    );
  } catch (err) {
    setError(err.message);
  }
}
    useEffect(() => {
    if (!token) return;

    carregarLeads();
  }, [token]);

  function formatarStatus(status) {
    const encontrado = STATUS_OPTIONS.find(
      ([codigo]) => codigo === status
    );

    return encontrado ? encontrado[1] : status || "Sem status";
  }

  function formatarObjetivo(objetivo) {
    const nomes = {
      informacao: "Informação",
      cotacao: "Cotação",
      contratacao: "Contratação",
    };

    return nomes[objetivo] || objetivo || "-";
  }

  function formatarStatus(status) {
  const nomes = {
    NOVO: "Novo",
    EM_QUALIFICACAO: "Em qualificação",
    PRONTO_PARA_CONSULTOR: "Pronto para consultor",
    ATRIBUIDO_AO_CONSULTOR: "Atribuído ao consultor",
    EM_CONTATO: "Em contato",
    COTACAO_REALIZADA: "Cotação realizada",
    PROPOSTA_ENVIADA: "Proposta enviada",
    CONTRATADO: "Contratado",
    SEM_RESPOSTA: "Sem resposta",
    DADOS_INCOMPLETOS: "Dados incompletos",
    SEM_INTERESSE: "Sem interesse",
    PERDIDO: "Perdido",
  };

  return nomes[status] || status || "-";
}

    if (!token) {
    return (
      <div className="app">
        <main className="content">
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Entrar no BEM MAIS-AI</h2>
                <p>Acesso ao painel de atendimento</p>
              </div>
            </div>

            <form
              onSubmit={async (event) => {
                event.preventDefault();

                const form = event.currentTarget;
                const email = form.email.value;
                const senha = form.senha.value;

                try {
                  setError("");
                  await fazerLogin(email, senha);
                } catch (err) {
                  setError(err.message);
                }
              }}
            >
              <div className="detail-group">
                <span>Email</span>
                <input
                  name="email"
                  type="email"
                  placeholder="seu@email.com"
                  required
                />
              </div>

              <div className="detail-group">
                <span>Senha</span>
                <input
                  name="senha"
                  type="password"
                  placeholder="Sua senha"
                  required
                />
              </div>

              {error && (
                <p className="message error">{error}</p>
              )}

              <button type="submit">
                Entrar
              </button>
            </form>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>BEM MAIS-AI</h1>
          <span>Plataforma comercial inteligente</span>
        </div>

        <nav className="sidebar-menu">
          <button
            className={`sidebar-item ${
              activePage === "dashboard" ? "active" : ""
            }`}
            onClick={() => setActivePage("dashboard")}
          >
            <span>⌂</span>
            <span>Dashboard</span>
          </button>

          <button
            className={`sidebar-item ${
              activePage === "leads" ? "active" : ""
            }`}
            onClick={() => setActivePage("leads")}
          >
            <span>◈</span>
            <span>Leads / CRM</span>
          </button>

          <button className="sidebar-item">
            <span>◌</span>
            <span>Atendimento</span>
          </button>

          {usuario?.role === "ADM" && (
            <button
              className={`sidebar-item ${
                activePage === "consultores" ? "active" : ""
              }`}
              onClick={() => setActivePage("consultores")}
            >
              <span>♙</span>
              <span>Consultores</span>
            </button>
          )}

          <button className="sidebar-item">
            <span>☎</span>
            <span>Discador IA</span>
          </button>

          <button className="sidebar-item">
            <span>▥</span>
            <span>Relatórios</span>
          </button>

          <button className="sidebar-item">
            <span>✦</span>
            <span>IA e Automações</span>
          </button>

          <button className="sidebar-item">
            <span>▤</span>
            <span>Base de Conhecimento</span>
          </button>

          <button className="sidebar-item">
            <span>⚙</span>
            <span>Configurações</span>
          </button>
        </nav>

        <div className="sidebar-user">
          <strong>{usuario?.nome || "Usuário"}</strong>
          <span>
            {usuario?.role === "ADM" ? "Administrador" : "Consultor"}
          </span>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div>
            <h1>BEM MAIS-AI</h1>
            <p>Painel de atendimento e pré-vendas</p>
          </div>

          <button onClick={carregarLeads}>
            Atualizar
          </button>
        </header>

        <main className="content">
       {activePage === "dashboard" && (
          <>
            <section className="summary">
              <div className="summary-card">
                <span>Total de leads</span>
                <strong>{leads.length}</strong>
              </div>

              <div className="summary-card">
                <span>Prontos para consultor</span>
                <strong>
                  {
                    leads.filter(
                      (lead) =>
                        lead.status === "PRONTO_PARA_CONSULTOR"
                    ).length
                  }
                </strong>
              </div>

              <div className="summary-card">
                <span>Em análise</span>
                <strong>
                  {
                    leads.filter(
                      (lead) =>
                        lead.status === "EM_QUALIFICACAO"
                    ).length
                  }
                </strong>
              </div>

              <div className="summary-card">
                <span>Interesse alto</span>
                <strong>
                  {
                    leads.filter(
                      (lead) => lead.nivel_interesse === "ALTO"
                    ).length
                  }
                </strong>
              </div>
            </section>

           <section className="dashboard-charts">
              <div className="dashboard-chart-card">
                <div className="dashboard-chart-header">
                  <div>
                    <h2>Vendas realizadas</h2>
                    <p>Leads com contratação concluída</p>
                  </div>

                  <strong>
                    {
                      leads.filter(
                        (lead) => lead.status === "CONTRATADO"
                      ).length
                    }
                  </strong>
                </div>

                <div className="dashboard-chart">
                  <div
                    className="dashboard-chart-bar"
                    style={{
                      width: `${
                        leads.length > 0
                          ? Math.min(
                              (leads.filter(
                                (lead) => lead.status === "CONTRATADO"
                              ).length /
                                leads.length) *
                                100,
                              100
                            )
                          : 0
                      }%`,
                    }}
                  />
                </div>

                <div className="dashboard-chart-footer">
                  <span>Contratados</span>
                  <span>
                    {
                      leads.filter(
                        (lead) => lead.status === "CONTRATADO"
                      ).length
                    }{" "}
                    de {leads.length}
                  </span>
                </div>
              </div>

              <div className="dashboard-chart-card">
                <div className="dashboard-chart-header">
                  <div>
                    <h2>Fila de espera</h2>
                    <p>Leads aguardando atendimento do consultor</p>
                  </div>

                  <strong>
                    {
                      leads.filter(
                        (lead) =>
                          lead.status === "PRONTO_PARA_CONSULTOR"
                      ).length
                    }
                  </strong>
                </div>

                <div className="dashboard-chart">
                  <div
                    className="dashboard-chart-bar"
                    style={{
                      width: `${
                        leads.length > 0
                          ? Math.min(
                              (leads.filter(
                                (lead) =>
                                  lead.status === "PRONTO_PARA_CONSULTOR"
                              ).length /
                                leads.length) *
                                100,
                              100
                            )
                          : 0
                      }%`,
                    }}
                  />
                </div>

                <div className="dashboard-chart-footer">
                  <span>Aguardando consultor</span>
                  <span>
                    {
                      leads.filter(
                        (lead) =>
                          lead.status === "PRONTO_PARA_CONSULTOR"
                      ).length
                    }{" "}
                    de {leads.length}
                  </span>
                </div>
              </div>

              <div className="dashboard-chart-card">
                <div className="dashboard-chart-header">
                  <div>
                    <h2>Perdas</h2>
                    <p>Leads classificados como perdidos</p>
                  </div>

                  <strong>
                    {
                      leads.filter(
                        (lead) => lead.status === "PERDIDO"
                      ).length
                    }
                  </strong>
                </div>

                <div className="dashboard-chart">
                  <div
                    className="dashboard-chart-bar"
                    style={{
                      width: `${
                        leads.length > 0
                          ? Math.min(
                              (leads.filter(
                                (lead) => lead.status === "PERDIDO"
                              ).length /
                                leads.length) *
                                100,
                              100
                            )
                          : 0
                      }%`,
                    }}
                  />
                </div>

                <div className="dashboard-chart-footer">
                  <span>Leads perdidos</span>
                  <span>
                    {
                      leads.filter(
                        (lead) => lead.status === "PERDIDO"
                      ).length
                    }{" "}
                    de {leads.length}
                  </span>
                </div>
              </div>
              <div className="dashboard-chart-card">
                <div className="dashboard-chart-header">
                  <div>
                    <h2>Sem resposta</h2>
                    <p>Leads que não responderam aos contatos</p>
                  </div>

                  <strong>
                    {
                      leads.filter(
                        (lead) => lead.status === "SEM_RESPOSTA"
                      ).length
                    }
                  </strong>
                </div>

                <div className="dashboard-chart">
                  <div
                    className="dashboard-chart-bar"
                    style={{
                      width: `${
                        leads.length > 0
                          ? Math.min(
                              (leads.filter(
                                (lead) => lead.status === "SEM_RESPOSTA"
                              ).length /
                                leads.length) *
                                100,
                              100
                            )
                          : 0
                      }%`,
                    }}
                  />
                </div>

                <div className="dashboard-chart-footer">
                  <span>Sem resposta</span>
                  <span>
                    {
                      leads.filter(
                        (lead) => lead.status === "SEM_RESPOSTA"
                      ).length
                    }{" "}
                    de {leads.length}
                  </span>
                </div>
              </div>
            </section>
          </>
        )}

        {usuario?.role === "ADM" && activePage === "consultores" && (
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Gestão de Consultores</h2>
                <p>
                  Consultores da sua empresa
                </p>
              </div>
            </div>

            <div className="consultants-list">
              {consultants.length === 0 ? (
                <p className="message">
                  Nenhum consultor cadastrado.
                </p>
              ) : (
                consultants.map((consultant) => (
                  <div
                    key={consultant.id}
                    className="consultant-card"
                  >
                    <div>
                      <strong>{consultant.nome}</strong>

                      <p>
                        {consultant.email || "E-mail não informado"}
                      </p>

                      <p>
                        {consultant.telefone || "Telefone não informado"}
                      </p>
                    </div>

                    <span>
                      {consultant.ativo === 1
                        ? "Ativo"
                        : "Inativo"}
                    </span>
                  </div>
                ))
              )}
            </div>
          </section>
        )}

       {activePage === "leads" && (
         <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Leads</h2>
              <p>Clientes captados pelo atendimento</p>
            </div>
          </div>

          {loading && (
            <p className="message">Carregando leads...</p>
          )}

          {error && (
            <p className="message error">{error}</p>
          )}

          {!loading && !error && leads.length === 0 && (
            <p className="message">
              Nenhum lead encontrado.
            </p>
          )}

          {!loading && !error && leads.length > 0 && (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Lead</th>
                    <th>Veículo</th>
                    <th>Localização</th>
                    <th>Objetivo</th>
                    <th>Interesse</th>
                    <th>Status</th>
                  </tr>
                </thead>

                <tbody>
                  {leads.map((lead) => (
                    <tr
                      key={lead.id}
                      className="lead-row"
                      onClick={() => abrirLead(lead.id)}
                    >
                      <td>
                        <strong>
                          {lead.nome || "Sem nome"}
                        </strong>
                        <small>#{lead.id}</small>
                      </td>

                      <td>
                        {lead.marca && lead.modelo
                          ? `${lead.marca} ${lead.modelo}`
                          : "-"}
                        {lead.ano && (
                          <small>{lead.ano}</small>
                        )}
                      </td>

                      <td>
                        {lead.cidade && lead.estado
                          ? `${lead.cidade} - ${lead.estado}`
                          : "-"}
                      </td>

                      <td>
                        {formatarObjetivo(lead.objetivo)}
                      </td>

                      <td>
                        <span className="interest">
                          {lead.nivel_interesse || "-"}
                        </span>
                      </td>

                      <td>
                        <span className="status">
                          {formatarStatus(lead.status)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

        {selectedLead && (
          <div
            className="modal-overlay"
            onClick={() => setSelectedLead(null)}
          >
            <div
              className="lead-modal"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="modal-header">
                <div>
                  <h2>
                    {selectedLead.nome || "Lead sem nome"}
                  </h2>
                  
                  <button
                    onClick={() => setShowLeadDetails(!showLeadDetails)}
                    className="details-button"
                  >
                    {showLeadDetails ? "Ocultar detalhes" : "Ver detalhes"}
                  </button>
                  
                  {showLeadDetails && (
                    <div className="lead-details">
                      <p><strong>Nome:</strong> {selectedLead.nome || "Não informado"}</p>
                      <p><strong>Veículo:</strong> {selectedLead.tipo_veiculo || "Não informado"}</p>
                      <p><strong>Marca:</strong> {selectedLead.marca || "Não informado"}</p>
                      <p><strong>Modelo:</strong> {selectedLead.modelo || "Não informado"}</p>
                      <p><strong>Ano:</strong> {selectedLead.ano || "Não informado"}</p>
                      <p><strong>Cidade:</strong> {selectedLead.cidade || "Não informado"}</p>
                      <p><strong>Estado:</strong> {selectedLead.estado || "Não informado"}</p>
                      <p><strong>Objetivo:</strong> {selectedLead.objetivo || "Não informado"}</p>
                      <p><strong>Interesse:</strong> {selectedLead.nivel_interesse || "Não informado"}</p>
                      <p><strong>Status:</strong> {selectedLead.status || "Não informado"}</p>
                      {usuario?.role === "CONSULTOR" && (
                        <div className="lead-status-control">
                          <label htmlFor="requested-status">
                            <strong>Solicitar alteração de status</strong>
                          </label>

                          <select
                            id="requested-status"
                            value={requestedStatus}
                            onChange={(e) => setRequestedStatus(e.target.value)}
                            disabled={savingStatusRequest}
                          >
                            <option value="">
                              Selecione o novo status
                            </option>

                            {statusDisponiveisParaSolicitacao
                              .filter(
                                (status) => status.value !== selectedLead.status
                              )
                              .map((status) => (
                                <option
                                  key={status.value}
                                  value={status.value}
                                >
                                  {status.label}
                                </option>
                              ))}
                          </select>

                          <textarea
                            value={requestReason}
                            onChange={(e) => setRequestReason(e.target.value)}
                            placeholder="Informe o motivo da alteração..."
                            rows={3}
                            disabled={savingStatusRequest}
                          />

                          <button
                            type="button"
                            onClick={solicitarAlteracaoStatus}
                            disabled={
                              savingStatusRequest ||
                              !requestedStatus
                            }
                          >
                            {savingStatusRequest
                              ? "Enviando..."
                              : "Solicitar alteração"}
                          </button>
                        </div>
                      )}
                      <div className="lead-status-control">
                        <label htmlFor="lead-status">
                          <strong>Status do lead</strong>
                        </label>

                        <select
                          id="lead-status"
                          value={selectedLead.status || ""}
                          onChange={async (e) => {
                            const novoStatus = e.target.value;

                            try {
                              setError("");

                              const response = await fetch(
                                `${API_URL}/api/leads/${selectedLead.id}`,
                                {
                                  method: "PATCH",
                                  headers: {
                                    Authorization: `Bearer ${token}`,
                                    "Content-Type": "application/json",
                                  },
                                  body: JSON.stringify({
                                    status: novoStatus,
                                  }),
                                }
                              );

                              if (!response.ok) {
                                const data = await response.json();
                                throw new Error(
                                  data.detail || "Não foi possível atualizar o status."
                                );
                              }

                              const leadAtualizado = await response.json();
                              setSelectedLead(leadAtualizado);

                              setLeads((listaAtual) =>
                                listaAtual.map((lead) =>
                                  lead.id === leadAtualizado.id
                                    ? leadAtualizado
                                    : lead
                                )
                              );
                            } catch (err) {
                              setError(err.message);
                            }
                          }}
                        >
                          <option value="NOVO">Novo</option>
                          <option value="EM_QUALIFICACAO">Em qualificação</option>
                          <option value="PRONTO_PARA_CONSULTOR">
                            Pronto para consultor
                          </option>
                          <option value="ATRIBUIDO_AO_CONSULTOR">
                            Atribuído ao consultor
                          </option>
                          <option value="EM_CONTATO">Em contato</option>
                          <option value="COTACAO_REALIZADA">
                            Cotação realizada
                          </option>
                          <option value="PROPOSTA_ENVIADA">
                            Proposta enviada
                          </option>
                          <option value="CONTRATADO">Contratado</option>
                          <option value="SEM_RESPOSTA">Sem resposta</option>
                          <option value="DADOS_INCOMPLETOS">
                            Dados incompletos
                          </option>
                          <option value="SEM_INTERESSE">Sem interesse</option>
                          <option value="PERDIDO">Perdido</option>
                        </select>
                      </div>
                      <p><strong>Consultor:</strong> {selectedLead.consultor_id || "Não atribuído"}</p>
                    </div>
                  )}

                  <p>Lead #{selectedLead.id}</p>
                </div>

                <button
                  className="close-button"
                  onClick={() => setSelectedLead(null)}
                >
                  ×
                </button>
              </div>

              <div className="lead-details">
                <div className="detail-group">
                  <span>Canal de origem</span>
                  <strong>
                    {selectedLead.canal_origem || "-"}
                  </strong>
                </div>

                <div className="detail-group">
                  <span>Tipo de veículo</span>
                  <strong>
                    {selectedLead.tipo_veiculo || "-"}
                  </strong>
                </div>

                <div className="detail-group">
                  <span>Marca</span>
                  <strong>
                    {selectedLead.marca || "-"}
                  </strong>
                </div>

                <div className="detail-group">
                  <span>Modelo</span>
                  <strong>
                    {selectedLead.modelo || "-"}
                  </strong>
                </div>

                <div className="detail-group">
                  <span>Ano</span>
                  <strong>
                    {selectedLead.ano || "-"}
                  </strong>
                </div>

                <div className="detail-group">
                  <span>Localização</span>
                  <strong>
                    {selectedLead.cidade && selectedLead.estado
                      ? `${selectedLead.cidade} - ${selectedLead.estado}`
                      : "-"}
                  </strong>
                </div>

                <div className="detail-group">
                  <span>Objetivo</span>
                  <strong>
                    {formatarObjetivo(selectedLead.objetivo)}
                  </strong>
                </div>

                <div className="detail-group">
                  <span>Plano de interesse</span>
                  <strong>
                    {selectedLead.plano_interesse || "-"}
                  </strong>
                </div>

                <div className="detail-group">
                  <span>Nível de interesse</span>
                  <strong>
                    {selectedLead.nivel_interesse || "-"}
                  </strong>
                </div>
                <div className="detail-group">
                  <span>Consultor responsável</span>

                  <select
                    className="status-select"
                    value={selectedLead.consultor_id || ""}
                    onChange={(event) =>
                      alterarConsultor(event.target.value)
                    }
                  >
                    <option value="">Não atribuído</option>

                    {consultants.map((consultant) => (
                      <option
                        key={consultant.id}
                        value={consultant.id}
                      >
                        {consultant.nome}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="detail-group">
                  <span>Status atual</span>

                  <select
                    className="status-select"
                    value={selectedLead.status || "NOVO"}
                    onChange={(event) =>
                      alterarStatus(event.target.value)
                    }
                    disabled={savingStatus}
                  >
                    {STATUS_OPTIONS.map(
                      ([codigo, nome]) => (
                        <option
                          key={codigo}
                          value={codigo}
                        >
                          {nome}
                        </option>
                      )
                    )}
                  </select>

                  {savingStatus && (
                    <small className="saving">
                      Salvando...
                    </small>
                  )}
                </div>

                <div className="detail-group full-width">
                  <span>Resumo</span>
                  <strong>
                    {selectedLead.resumo ||
                      "Ainda não informado."}
                  </strong>
                </div>
              </div>

              <div className="conversation-section">
                <div className="conversation-header">
                  <div>
                    <h3>Histórico da conversa</h3>
                    <p>
                      Mensagens trocadas durante o atendimento
                    </p>
                  </div>
                </div>

                {loadingMessages ? (
                  <p className="message">
                    Carregando histórico...
                  </p>
                ) : messages.length === 0 ? (
                  <p className="message">
                    Nenhuma mensagem encontrada.
                  </p>
                ) : (
                  <div className="conversation">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`message-bubble ${
                          message.role === "user"
                            ? "user-message"
                            : message.role === "consultant"
                            ? "consultant-message"
                            : "assistant-message"
                        }`}
                      >
                        <span className="message-role">
                          {message.author_name ||
                            (message.role === "user"
                              ? "Cliente"
                              : message.role === "assistant"
                              ? "BEM MAIS-AI"
                              : "Consultor")}
                        </span>

                        <p>{message.content}</p>
                      </div>
                    ))}
                  </div>
                )}

                {selectedLead && (
                  <div className="message-composer">
                    <textarea
                      value={consultantMessage}
                      onChange={(e) => setConsultantMessage(e.target.value)}
                      placeholder="Digite uma mensagem para o cliente..."
                      rows={3}
                    />

                    <button
                      onClick={enviarMensagemConsultor}
                      disabled={!consultantMessage.trim()}
                    >
                      Enviar mensagem
                    </button>
                  </div>
                )}
              </div>

              {usuario?.role === "ADM" && (
                <div className="conversation-section">
                  <div className="conversation-header">
                    <div>
                      <h3>Histórico de status</h3>
                      <p>
                        Alterações de status realizadas no lead
                      </p>
                    </div>
                  </div>

                  {statusHistory.length === 0 ? (
                    <p className="message">
                      Nenhuma alteração de status registrada.
                    </p>
                  ) : (
                    <div className="conversation">
                      {statusHistory.map((item) => (
                        <div
                          key={item.id}
                          className="message-bubble assistant-message"
                        >
                          <span className="message-role">
                            Status alterado
                          </span>

                          <p>
                            <strong>De:</strong>{" "}
                            {formatarStatus(item.old_status)}
                          </p>

                          <p>
                            <strong>Para:</strong>{" "}
                            {formatarStatus(item.new_status)}
                          </p>

                          <small>
                            {item.changed_by_user_name || `Usuário #${item.changed_by_user_id}`}
                            {" • "}
                            {new Date(item.created_at).toLocaleString("pt-BR")}
                          </small>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

             {usuario?.role === "ADM" && (
                <div className="conversation-section">
                  <div className="conversation-header">
                    <div>
                      <h3>Histórico de atribuições</h3>
                      <p>
                        Alterações de responsável pelo lead
                      </p>
                    </div>
                  </div>

                  {assignmentHistory.length === 0 ? (
                    <p className="message">
                      Nenhuma alteração de responsável registrada.
                    </p>
                  ) : (
                    <div className="conversation">
                      {assignmentHistory.map((item) => (
                        <div
                          key={item.id}
                          className="message-bubble assistant-message"
                        >
                          <span className="message-role">
                            {item.action === "ATRIBUIDO"
                              ? "Lead atribuído"
                              : item.action === "REMOVIDO"
                              ? "Consultor removido"
                              : "Lead transferido"}
                          </span>

                          <p>
                            <strong>Consultor:</strong>{" "}
                            {item.consultant_name ||
                              (item.consultant_id
                                ? `Consultor #${item.consultant_id}`
                                : "Nenhum")}
                          </p>

                          <small>
                            Alterado por:{" "}
                            {item.changed_by_user_name ||
                              `Usuário #${item.changed_by_user_id}`}
                            {" • "}
                            {new Date(item.created_at).toLocaleString("pt-BR")}
                          </small>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
       </main>
      </div>
    </div>
  );
}

export default App;
