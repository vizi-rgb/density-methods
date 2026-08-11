# syntax=docker/dockerfile:1

# Build context is the *parent* directory (density-methods/), not this repo,
# because `lib` (density-methods) is consumed as a sibling editable dependency
# (see pyproject.toml [tool.uv.sources]) and its source must be present in the
# image — see docker-compose.yml's `context: ..`.
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /usr/local/bin/

WORKDIR /workspace
COPY ./heatmaps-backend/pyproject.toml ./heatmaps-backend/uv.lock ./heatmaps-backend/
COPY ./lib/pyproject.toml ./lib/uv.lock ./lib/

WORKDIR /workspace/heatmaps-backend
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

ENV PATH="/workspace/heatmaps-backend/.venv/bin:${PATH}"

COPY ./lib /workspace/lib/
COPY ./heatmaps-backend ./

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
