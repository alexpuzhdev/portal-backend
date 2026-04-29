FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# uv binary copied from the official image — pinned by the Renovate-friendly tag.
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /usr/local/bin/

WORKDIR /workspace

# Зависимости устанавливаются по lockfile из workspace root, без копирования исходников —
# даёт переиспользование кеша слоёв.
COPY pyproject.toml uv.lock ./
COPY apps/core/pyproject.toml apps/core/pyproject.toml
COPY packages/canonical-models/pyproject.toml packages/canonical-models/pyproject.toml
COPY packages/connector-sdk/pyproject.toml packages/connector-sdk/pyproject.toml
COPY packages/event-schemas/pyproject.toml packages/event-schemas/pyproject.toml

RUN uv sync --all-packages --frozen --no-install-project --no-dev

COPY packages/ packages/
COPY apps/core/ apps/core/

RUN uv sync --all-packages --frozen --no-dev

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /workspace/apps/core

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
