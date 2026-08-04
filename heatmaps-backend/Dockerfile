# Build context is the *parent* directory (density-methods/), not this repo,
# because `lib` (density-methods) is consumed as a sibling editable dependency
# (see pyproject.toml [tool.uv.sources]) and its source must be present in the
# image — see docker-compose.yml's `context: ..`.
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /workspace
COPY lib ./lib
COPY heatmaps-backend ./heatmaps-backend

WORKDIR /workspace/heatmaps-backend
# NOT --no-dev: `density-methods` (../lib) is registered under the dev
# dependency group (per project convention) but is a genuine runtime
# dependency — the worker imports it to do the actual video analysis.
RUN uv sync --frozen

ENV PATH="/workspace/heatmaps-backend/.venv/bin:${PATH}"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
