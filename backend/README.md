# Backend Synapse

API em Django + Django REST Framework, com banco PostgreSQL.

## Requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker](https://www.docker.com/products/docker-desktop/) (para rodar o PostgreSQL localmente)

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

O Django lê o `.env` sozinho, então os comandos abaixo não precisam de `--env-file`.

## Banco de dados (PostgreSQL)

Suba um PostgreSQL 16 com Docker. Os dados batem com o `DATABASE_URL` do `.env.example`:

```bash
docker run -d --name synapse-postgres -e POSTGRES_USER=synapse -e POSTGRES_PASSWORD=synapse -e POSTGRES_DB=synapse -p 5432:5432 postgres:16
```

Nos próximos dias, para religar o banco depois de reiniciar o computador:

```bash
docker start synapse-postgres
```

Crie as tabelas (rode de novo sempre que alguém adicionar uma migração):

```bash
uv run python manage.py migrate
```

Se você alterar um model, gere a migração e faça commit dela junto:

```bash
uv run python manage.py makemigrations
```

> O Docker Compose com banco, backend e frontend juntos vem na issue #4.

## Rodar

```bash
uv run python manage.py runserver
```

- Health check: http://localhost:8000/health
- Swagger: http://localhost:8000/docs/
- Schema OpenAPI: http://localhost:8000/schema/
- Django Admin: http://localhost:8000/admin/

## Django Admin

O Admin permite ver e editar os dados do banco pelo navegador. Para entrar, crie um superusuário (o login é pelo e-mail):

```bash
uv run python manage.py createsuperuser
```

## Usuários

O projeto usa um modelo de usuário próprio, `UsuarioModel` (em `app/infra/modelos/usuario.py`), configurado em `AUTH_USER_MODEL`:

- login por **e-mail** (não existe campo `username`);
- identificador **UUID**;
- o e-mail é guardado em minúsculas e é único.

Para se referir ao usuário em outros models, use `settings.AUTH_USER_MODEL` (ou `get_user_model()` no código), e nunca `django.contrib.auth.models.User`.

## Testar

Com o PostgreSQL rodando:

```bash
uv run pytest
```

O `pytest-django` cria um banco separado para os testes (`test_synapse`) e o apaga no fim, então os testes nunca mexem nos dados de desenvolvimento. Testes que acessam o banco precisam da marcação `@pytest.mark.django_db`.

## Lint e formatação

```bash
uv run ruff check .
uv run ruff format .
```

## Estrutura

```
backend/
├── config/            # projeto Django (settings, urls, wsgi, asgi)
├── app/
│   ├── domain/        # regras de negócio puras (sem Django)
│   ├── application/   # serviços / casos de uso
│   ├── infra/
│   │   └── modelos/   # models do Django (persistência)
│   ├── api/           # views e serializers (DRF)
│   ├── migrations/    # migrações do banco
│   ├── models.py      # reexporta os models de infra/modelos para o Django
│   └── admin.py       # configuração do Django Admin
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
| `DATABASE_URL` | conexão com o PostgreSQL: `postgres://usuario:senha@host:porta/banco` |
