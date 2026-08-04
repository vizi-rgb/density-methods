# heatmaps-backend

FastAPI service that accepts an uploaded video, analyzes it with the
[`density-methods`](../lib) library (YOLO tracking + heatmap builders), and
serves the resulting heatmap-overlay videos as HLS for `heatmaps-frontend`
(`hls.js`) to play.

Full design docs: [`docs/implementation-plan.md`](docs/implementation-plan.md),
[`docs/api-contract.md`](docs/api-contract.md),
[`docs/acceptance-criteria.md`](docs/acceptance-criteria.md).

## Requirements

- Python 3.13, [uv](https://docs.astral.sh/uv/)
- `ffmpeg` on `PATH`
- Redis (a local `redis-server`, or use `docker-compose up redis`)
- The sibling `../lib` (`density-methods`) checkout — consumed as an editable
  dev dependency (`[tool.uv.sources]` in `pyproject.toml`), never copied here.

## Running locally

```bash
uv sync
redis-server --daemonize yes   # or: docker compose up -d redis

# terminal 1
uv run uvicorn app.main:app --reload

# terminal 2 — SimpleWorker avoids a macOS fork/Objective-C crash some of
# lib's dependencies (torch/opencv) trigger under RQ's default fork-per-job
# worker, and matches this project's single-sequential-worker v1 design.
uv run rq worker --worker-class rq.worker.SimpleWorker video-processing
```

Then `POST` a video to `http://localhost:8000/api/upload` (see
[`docs/api-contract.md`](docs/api-contract.md)) and poll/stream
`/api/status/{job_id}`.

**If a job's progress is stuck at 0%**, check `GET /health` first —
`workers_online: 0` with `queued_jobs > 0` means terminal 2 above isn't
running (the single most common local-dev mistake here: uploads are
accepted and queue fine even with no worker at all, so there's otherwise no
visible symptom until you check).

Config is env-driven (`pydantic-settings`, see `app/config.py`) — copy
`.env.example` to `.env` to override defaults locally.

## Running with Docker Compose

```bash
docker compose up --build
```

Brings up `redis`, `api` (port 8000), and `worker` together. The build
context is the **parent** directory (`density-methods/`), not this repo,
because the image needs `../lib`'s source alongside this project's — see
comments in `Dockerfile`/`docker-compose.yml`.

## Tests

```bash
uv run pytest -m "not integration"   # fast: unit tests + HTTP wiring (fakeredis)
uv run pytest -m integration         # slow: real YOLO pipeline against a real clip
uv run ruff check .
uv run mypy app tests
```

The `integration`-marked test needs `../lib/data/weights/*.pt` and
`../lib/data/datasets/yt/walking_people.mp4`, both gitignored in `lib/` (not
committed) — present if you already have `lib` set up locally, absent on a
fresh clone/in CI. CI runs `-m "not integration"` for that reason.

## Known v1 limitations

- Redis is the sole job-state store — job history is lost if Redis data is
  flushed or a job's TTL (`job_ttl_seconds`) expires.
- Single sequential worker — jobs are processed one at a time, no
  concurrency, by design (the ML pipeline is CPU/GPU-heavy).
- Only `directional`/`speed`/`cluster` heatmap types are supported. `roi`/
  `tripwire` need user-supplied geometry (polygon/tripwire line) that no UI
  collects yet.
- Only `lib`'s `YOLOModel` is used — `YOLOCrowdModel` doesn't support
  tracking in `lib` today.
- `speed` heatmap uses real-world km/h via `lib`'s `CameraToWorldMapper`, but
  its `CameraInfo` calibration keypoints are hardcoded to one specific
  reference video's camera perspective — speed values for other footage are
  only as accurate as that calibration happens to be for it.
- Uploaded source videos and generated HLS output under `data/` are kept
  indefinitely — no automated retention/cleanup yet.
