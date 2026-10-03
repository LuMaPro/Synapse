# Backend Synapse

API em Django + Django REST Framework.

## Requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Instalar

```bash
cd backend
uv sync
cp .env.example .env
```

No Windows (PowerShell), use `Copy-Item .env.example .env`.

Depois edite o `.env` e troque o `SECRET_KEY` por uma chave sua. Para gerar:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Rodar

```bash
uv run --env-file .env python manage.py runserver
```

- Health check: http://localhost:8000/health
- Swagger: http://localhost:8000/docs/
- Schema OpenAPI: http://localhost:8000/schema/

## Testar

```bash
uv run --env-file .env pytest
```

## Lint e formatação

```bash
uv run ruff check .
uv run ruff format .
```

## Estrutura

```
backend/
├── config/          # projeto Django (settings, urls, wsgi, asgi)
├── app/
│   ├── domain/      # regras de negócio puras (sem Django)
│   ├── application/ # serviços / casos de uso
│   ├── infra/       # models e repositórios (ORM)
│   └── api/         # views e serializers (DRF)
└── tests/
    ├── unit/
    └── integration/
```

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `SECRET_KEY` | chave secreta do Django |
| `DEBUG` | `True` em desenvolvimento |
| `ALLOWED_HOSTS` | hosts permitidos, separados por vírgula |