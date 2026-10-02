# BEM MAIS-AI

MVP da plataforma de atendimento e pré-vendas da Bem Mais Mutual.

## Stack inicial

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy
- Docker
- Camada preparada para integração com modelo de IA

## Executar

1. Copie `backend/.env.example` para `backend/.env`.
2. Execute:

```bash
docker compose up
```

3. API:
   - http://localhost:8000
   - Documentação: http://localhost:8000/docs

## Teste do chat

POST `/api/chat`

```json
{
  "session_id": "teste-001",
  "message": "Olá, quero fazer uma cotação para meu carro"
}
```

## Observação

Não há conteúdo comercial fictício incorporado ao sistema. A base oficial da empresa deve ser adicionada em `knowledge/bem_mais_mutual/` antes de habilitar respostas comerciais reais.
