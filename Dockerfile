# Environnement figé de Vigenère-Squad (CPU, sans GPU).
# Utilisation recommandée : docker compose (voir compose.yaml et README).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

WORKDIR /app
# Dépendances d'abord (cache des couches), versions exactes de uv.lock
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen

ENTRYPOINT ["uv", "run", "--frozen", "vsquad"]
CMD ["--help"]
