# heatmaps-backend

FastAPI service that accepts an uploaded video, then lets you incrementally
request individual heatmap analyses (directional / speed / cluster / tripwire
/ roi, each with its own parameters) against it via the
[`density-methods`](../lib) library (YOLO tracking + heatmap builders).
Every result — the raw upload preview and every heatmap analysis — is a
plain MP4 for `heatmaps-frontend` to play with a plain `<video>` tag (no
HLS/`hls.js` — see `docs/implementation-plan.md` for why).

Full design docs: [`docs/implementation-plan.md`](docs/implementation-plan.md),
[`docs/api-contract.md`](docs/api-contract.md),
[`docs/acceptance-criteria.md`](docs/acceptance-criteria.md).

## Requirements

- Python 3.13, [uv](https://docs.astral.sh/uv/)
- `ffmpeg` on `PATH`
- Redis (a local `redis-server`, or `docker compose up -d redis`)
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

Basic flow (see [`docs/api-contract.md`](docs/api-contract.md) for full detail):

```bash
# 1. upload once
curl -F "file=@video.mp4" http://localhost:8000/api/videos
# -> {"video_id": "...", "video_url": "http://localhost:8000/media/videos/.../source.mp4"}

# 2. (optional) calibrate perspective for accurate real-world speed —
#    skip this and speed heatmaps fall back to a hardcoded reference matrix
curl -X POST http://localhost:8000/api/videos/{video_id}/calibration \
  -H "Content-Type: application/json" \
  -d '{"camera_points":[[293,174],[40,557],[1752,524],[1512,149]],"real_world_points":[[0,0],[0,6],[15,6],[15,0]]}'

# 3. add as many analyses as you want against that video_id
curl -X POST http://localhost:8000/api/videos/{video_id}/heatmaps \
  -H "Content-Type: application/json" -d '{"type":"directional","direction":"right"}'
# -> {"job_id": "..."}

# 4. poll or stream each job independently
curl http://localhost:8000/api/heatmaps/{job_id}
curl -N http://localhost:8000/api/heatmaps/{job_id}/stream
```

**If a job's progress is stuck at 0%**, check `GET /health` first —
`workers_online: 0` with `queued_jobs > 0` means terminal 2 above isn't
running (the single most common local-dev mistake here: uploads/job
creation succeed and queue fine even with no worker at all, so there's
otherwise no visible symptom until you check).

Config is env-driven (`pydantic-settings`, see `app/config.py`) — copy
`.env.example` to `.env` to override defaults locally.

## Running with Docker Compose

```bash
docker compose up --build
```

Brings up `redis`, `api` (port 8000), and `worker` together. The build
context is the **parent** directory (`density-methods/`), not this repo,
because the image needs `../lib`'s source alongside this project's — see
comments in `Dockerfile`/`docker-compose.yml`. **Not verified by an actual
run** in the environment this was built in (no Docker available there) —
treat as unverified until someone runs it for real.

## Tests

```bash
uv run pytest -m "not integration"   # fast: unit tests + HTTP wiring (fakeredis)
uv run pytest -m integration         # slow: real YOLO pipeline, all 5 heatmap types, against a real clip
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
- Single sequential worker — jobs are processed one at a time, by design
  (the ML pipeline is CPU/GPU-heavy).
- All 5 heatmap types are supported: `directional`/`speed`/`cluster` plus
  `roi`/`tripwire` (user-drawn polygon / line+inside-point, collected via a
  Konva picker in `heatmaps-frontend`).
- `speed` uses real-world km/h via `lib`'s `CameraToWorldMapper`. Its
  transformation matrix is now calibratable per-video via
  `POST /api/videos/{video_id}/calibration` (4-point pixel↔real-world
  correspondence); a video that was never calibrated falls back to `lib`'s
  `CameraInfo` — hardcoded to one specific reference video's camera
  perspective — so accuracy for uncalibrated footage still depends on how
  close that fallback calibration happens to be.
- No dedup — re-uploading the same video content creates a new `video_id`
  and a new copy on disk. Considered, explicitly out of scope for now.
- Uploaded videos and job outputs under `data/` are kept indefinitely — no
  automated retention/cleanup yet.
