FROM python:3.12-slim

# traz o uv para dentro da imagem
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# o ambiente virtual fica fora de /app (explico abaixo)
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# copia só as dependências primeiro, para aproveitar o cache
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# depois copia o código
COPY . .

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]