# AGENTS.md — heatmaps-backend

FastAPI service: accepts an uploaded video, analyzes it with the sibling
`../lib` (`density-methods`) library, serves the resulting heatmap-overlay
videos as HLS for `heatmaps-frontend` (`hls.js`) to play.

Full design docs — read these before making non-trivial changes:
- [`docs/implementation-plan.md`](docs/implementation-plan.md) — architecture, module layout, pipeline/HLS design.
- [`docs/api-contract.md`](docs/api-contract.md) — authoritative wire contract with the frontend.
- [`docs/acceptance-criteria.md`](docs/acceptance-criteria.md) — Definition of Done, and what's actually verified vs. assumed.
- [`README.md`](README.md) — setup/run/test commands, known v1 limitations.

## Stack

Python 3.13, `uv`, FastAPI, Redis + RQ (job queue), `ffmpeg` (subprocess, HLS
encoding), `pydantic-settings` (config). `lib` (`density-methods`) is a
sibling uv project consumed as an **editable dev dependency**
(`[tool.uv.sources]` in `pyproject.toml`) — never copy its files into this
repo. It provides YOLO tracking + heatmap builders; there's no single
video-in/heatmap-out entrypoint in `lib` itself — `app/services/pipeline.py`
is the orchestration wrapper.

## Layout

```
app/
  main.py              # FastAPI app factory
  config.py             # pydantic-settings; HEATMAP_TYPES constant lives here
  api/routes/           # upload.py, status.py (snapshot + SSE), health.py
  api/schemas.py, errors.py
  domain/job.py          # JobStatus/JobState — maps RQ job status+meta -> API shape
  services/pipeline.py   # lib orchestration: model -> adapter -> momentum -> builders -> visualizer
  services/hls_encoder.py # per-heatmap-type ffmpeg subprocess (rawvideo stdin -> VOD HLS)
  services/storage.py     # upload/job output paths, manifest URL building
  worker/queue.py, tasks.py  # RQ queue + the process_video job function
tests/unit/, tests/integration/
```

## Commands

```bash
uv sync
redis-server --daemonize yes                                   # or: docker compose up -d redis
uv run uvicorn app.main:app --reload                            # terminal 1
uv run rq worker --worker-class rq.worker.SimpleWorker video-processing   # terminal 2 — see gotcha below

uv run pytest -m "not integration"   # fast: unit + HTTP wiring (fakeredis)
uv run pytest -m integration         # slow: real YOLO pipeline, needs lib's weights+sample video
uv run ruff check .
uv run mypy app tests
```

CI (`.github/workflows/heatmaps-backend-ci.yml`, at repo root — this is a
monorepo) runs ruff/mypy/`pytest -m "not integration"` on push/PR touching
`heatmaps-backend/` or `lib/`.

## Non-obvious things worth knowing before touching this code

- **"Upload succeeds but progress bar is stuck at 0%" almost always means no
  `rq worker` process is running.** Confirmed live: a job sits `queued`
  forever with zero symptom other than that, since `uvicorn` and `rq worker`
  are separate processes and it's easy to only start the first. Check
  `GET /health` — `workers_online: 0` with `queued_jobs > 0` is the exact
  signature. This is why that field exists on `/health` at all; don't remove
  it without another way to diagnose the same failure.
- **Always use `--worker-class rq.worker.SimpleWorker`.** RQ's default
  fork-per-job worker crashes on macOS (`objc[...]: +[NSNumber initialize]
  may have been in progress...`) because torch/opencv link Objective-C
  runtime bits that aren't fork-safe. `SimpleWorker` (no fork, one job at a
  time in-process) sidesteps it and matches this project's documented v1
  design (single sequential worker) anyway. `docker-compose.yml` already
  uses it.
- **`lib/core/momentum/` stays unchanged — by explicit product decision.**
  `MomentumTracker.update_batch`'s no-mapper branch has a real bug (crashes
  unconditionally — a 3-tuple unpack against a 2-element `zip`), but it's
  never exercised because `pipeline.py` always builds and passes a
  `CameraToWorldMapper`. Don't "fix" it in `lib` again — if you ever need
  the no-mapper path, fix it in a way that doesn't require touching `lib`,
  or raise it with whoever owns `lib`.
- **Speed uses real-world km/h**, via `CameraToWorldMapper(CameraInfo()
  .get_transformation_matrix())`, always constructed in `pipeline.py`'s
  `run()`. `CameraInfo`'s keypoints are a hardcoded perspective calibration
  for one specific reference video — speed values for other footage are
  only as accurate as that calibration happens to be for it. This is a
  known, accepted limitation (product decision), not a bug to fix here.
- **Only `directional`/`speed`/`cluster` are supported.** `roi`/`tripwire`
  need user-supplied geometry (polygon / tripwire line) that no UI collects.
  `HEATMAP_TYPES` in `app/config.py` is the source of truth for what's
  accepted at upload time.
- **Cluster heatmap has dynamic, unbounded dict keys** (one per distinct
  cluster size DBSCAN finds that frame) — there's no fixed sub-key like
  directional's `"all"`. `_ClusterTrack.frame()` in `pipeline.py` sums across
  whatever buckets exist that frame. If you touch this, keep that reduction.
- **`lib` is only pip-installable at all because of a packaging fix** in
  `lib/pyproject.toml` (`[build-system]` + `packages = ["core", "config",
  "models"]` + `include = ["project_root.py"]`). `lib`'s modules use bare
  absolute imports (`from core.heatmap... import`, `from project_root import
  PROJECT_ROOT`) rather than a `density_methods` namespace — that's why it's
  exposed as three top-level packages instead of one, and must stay that way
  unless every import in `lib` is rewritten too.
- **`density-methods` is a *dev* dependency but a real *runtime*
  dependency of the worker.** Don't add `--no-dev` to `uv sync` in the
  Dockerfile — the worker process needs it. See the comment in `Dockerfile`.
- **`docker-compose.yml`'s build `context` is the parent directory**
  (`..`, i.e. `density-methods/`), not this repo — because the image needs
  `../lib`'s source alongside this project's. Not verified by an actual
  `docker compose build` run (no Docker in the environment this was built
  in) — treat as unverified until someone runs it.
- **Weight files and the sample video are gitignored** in `lib/`
  (`lib/data/weights/*.pt`, `lib/data/datasets/yt/walking_people.mp4`) — present
  locally if `lib` is already set up, absent on a fresh clone/in CI. That's
  why the real-pipeline integration test is excluded from CI (`-m "not
  integration"`) and self-skips if the sample video is missing.
- **API contract is authoritative in `docs/api-contract.md` and must stay
  in lockstep with `heatmaps-frontend/docs/api-integration.md`.** Outputs
  are an *array* of `{type, label, manifest_url}` (one per selected type,
  order = request order), not a map — this was deliberately changed from an
  earlier draft to match the frontend's already-built shape. Status/SSE
  paths are `/api/status/{job_id}` and `/api/status/{job_id}/stream`, not
  `/api/jobs/...`.
- **Known frontend-side gap**: the frontend doesn't send `heatmap_types` on
  upload yet (documented in its own `api-integration.md`). Uploads without
  it currently 400.
