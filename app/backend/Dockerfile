FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependências primeiro (cache de camada); o lock garante versões fixas.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY tests ./tests
RUN uv sync --frozen

# Sem privilégios de root (ADR-0002).
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000
# O nginx do contêiner web publica a API em /api e remove o prefixo; --root-path informa isso ao OpenAPI.
CMD ["uvicorn", "inspire.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--root-path", "/api"]
