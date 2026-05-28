FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY actions ./actions
COPY data ./data
COPY config.yml domain.yml credentials.yml endpoints.yml endpoints.docker.yml ./

RUN uv run rasa train --config config.yml --domain domain.yml --data data/main --out models

EXPOSE 5005 5055

CMD ["uv", "run", "rasa", "run", "--enable-api", "--cors", "*", "--credentials", "credentials.yml", "--endpoints", "endpoints.docker.yml", "--model", "models", "--interface", "0.0.0.0", "--port", "5005"]
