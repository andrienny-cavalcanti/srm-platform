import re


def classify_intent(message: str) -> str:
    text = message.lower()

    if any(term in text for term in [
        "contratar",
        "quero contratar",
        "fechar",
        "adesão",
        "adesao"
    ]):
        return "contratacao"

    if any(term in text for term in [
        "cotação",
        "cotacao",
        "preço",
        "preco",
        "valor",
        "quanto custa"
    ]):
        return "cotacao"

    return "informacao"


def extract_lead_data(message: str) -> dict:
    """
    Extrai dados básicos do lead a partir da mensagem.
    Retorna apenas informações identificadas com segurança.
    """

    data = {}
    text = message.strip()

    # Nome: "Meu nome é André" / "Meu nome e André"
    match = re.search(
        r"(?:meu nome é|meu nome e|sou)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,3})",
        text,
        re.IGNORECASE
    )

    if match:
        data["nome"] = match.group(1).strip()

    # Ano do veículo: 2000-2099
    match = re.search(r"\b(20\d{2})\b", text)

    if match:
        data["ano"] = int(match.group(1))

    # Estado brasileiro por sigla
    estados = [
        "AC", "AL", "AP", "AM", "BA", "CE", "DF",
        "ES", "GO", "MA", "MT", "MS", "MG", "PA",
        "PB", "PR", "PE", "PI", "RJ", "RN", "RS",
        "RO", "RR", "SC", "SP", "SE", "TO"
    ]

    estado_match = re.search(
        r"(?:-|/|,\s*|\s+)([A-Z]{2})\b",
        text.upper()
    )

    if estado_match and estado_match.group(1) in estados:
        data["estado"] = estado_match.group(1)

        # Cidade e estado
    location_match = re.search(
        r"(?:moro em|moro na cidade de|sou de)\s+(.+?)(?:\s*[-/,]\s*([A-Za-z]{2}))?$",
        text,
        re.IGNORECASE
    )

    if location_match:
        cidade = location_match.group(1).strip()
        estado = location_match.group(2)

        if estado:
            estado = estado.upper()

        data["cidade"] = cidade

        if estado:
            data["estado"] = estado

  	    # Marca e modelo
    vehicle_match = re.search(
        r"\b(?:um|uma)\s+([A-Za-zÀ-ÿ]+)\s+([A-Za-zÀ-ÿ0-9-]+)",
        text,
        re.IGNORECASE
    )

    if vehicle_match:
        data["marca"] = vehicle_match.group(1).strip()
        data["modelo"] = vehicle_match.group(2).strip()

    # Tipo de veículo
    tipos = {
        "carro": "carro",
        "automóvel": "carro",
        "automovel": "carro",
        "moto": "moto",
        "motocicleta": "moto",
        "caminhão": "caminhao",
        "caminhao": "caminhao"
    }

    text_lower = text.lower()

    for termo, tipo in tipos.items():
        if termo in text_lower:
            data["tipo_veiculo"] = tipo
            break

    # Objetivo
    intent = classify_intent(message)

    if intent in ["cotacao", "contratacao"]:
        data["objetivo"] = intent

    return data


def generate_reply(message: str, intent: str, lead_data: dict | None = None) -> str:
    lead_data = lead_data or {}

    if not lead_data.get("nome"):
        return "Para começar, qual é o seu nome?"

    if not lead_data.get("tipo_veiculo"):
        return "Obrigado, {}! Qual é o tipo do veículo que você deseja proteger? (carro, moto ou caminhão)".format(
            lead_data["nome"]
        )

    if not lead_data.get("marca") or not lead_data.get("modelo"):
        return "Perfeito, {}! Qual é a marca e o modelo do veículo?".format(
            lead_data["nome"]
        )

    if not lead_data.get("ano"):
        return "Qual é o ano do veículo?".format(
            lead_data["nome"]
        )

    if not lead_data.get("cidade") or not lead_data.get("estado"):
        return "Em qual cidade e estado você mora?"

    if intent == "cotacao":
        return (
            "Perfeito, {}! Já tenho as informações principais. "
            "Vou organizar seu atendimento para um consultor continuar a cotação."
        ).format(lead_data["nome"])

    if intent == "contratacao":
        return (
            "Perfeito, {}! Já tenho as informações principais. "
            "Vou organizar seu atendimento para um consultor continuar a contratação."
        ).format(lead_data["nome"])

    return (
        "Obrigado, {}! Já tenho as informações principais. "
        "Vou organizar seu atendimento para um consultor continuar."
    ).format(lead_data["nome"])