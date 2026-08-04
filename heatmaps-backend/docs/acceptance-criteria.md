# Acceptance Criteria — heatmaps-backend

Definition-of-Done checklist for the v1 backend described in `implementation-plan.md` / `api-contract.md`. A change is not "done" until every applicable item below is checked.

Checked items below were actually verified (real upload through a live worker + `ffprobe`, or an automated test) during this implementation pass, not just implemented-and-assumed-correct. Unchecked items are either genuinely not done, or implemented but not yet exercised by a real test — each says which.

## Functional

- [x] Uploading a valid video with a valid `heatmap_types` selection produces a job that reaches `completed`, with one independently playable HLS manifest per selected type. Verified end-to-end with a real upload through a real worker + `ffprobe` on the output segment (h264, correct dimensions/fps/duration) + visual frame inspection showing real heatmap trails.
- [x] Selecting `roi`/`tripwire`/an unknown type, or an empty `heatmap_types`, is rejected at upload time (`422` for an invalid/empty value present in the request; `400` if the field is missing from the request entirely — see `api-contract.md`) — no job is created. Covered by `tests/unit/test_upload_validation.py` and `tests/integration/test_upload_flow.py`.
- [x] Uploading a non-video file, or a file exceeding `MAX_UPLOAD_MB`, is rejected (`415`/`413`) — no job is created. Validation checks actual file content (magic bytes via `filetype`), not just filename extension or client-supplied content-type header. Covered by `tests/integration/test_upload_flow.py`.
- [x] A mid-job pipeline failure causes the job to reach `failed` with a descriptive `error` message (not the generic RQ fallback), and in-flight ffmpeg encoders are killed rather than left running. Covered by `tests/unit/test_worker_tasks.py`. Not separately tested: a genuinely corrupt/unsupported-codec *input video* reaching the same path (only a synthetic pipeline exception was tested) — `pipeline.read_metadata`'s fps/frame-count checks are the intended guard there but aren't exercised by a real corrupt file in the test suite.
- [x] Progress reported via SSE/`GET /api/status/{id}` is monotonically non-decreasing and only reaches 100 at `completed` (capped at 99 while processing). Observed in a real run (26→40→53→66→80→93→completed/100) and covered by `tests/unit/test_worker_tasks.py`.
- [x] After an SSE disconnect or a frontend page reload mid-job, `GET /api/status/{job_id}` returns the correct current state. Covered by `tests/integration/test_upload_flow.py`; also exercised manually by polling a real job to completion.
- [ ] Multiple jobs uploaded concurrently are all accepted, queue correctly, and are processed without cross-job state leakage. Not tested with genuine concurrency — reasoning (per-job UUID directories, no shared mutable state across `run_job` calls) supports it, but this is a real gap, not a verified guarantee, especially once a real (forking or threaded) worker replaces the single `SimpleWorker`.
- [x] `lib`'s `YOLOModel` path (not `YOLOCrowdModel`, which lacks tracking support) is the one used — true by construction, `pipeline.py` never references `YOLOCrowdModel`.

## Code quality

- [x] `lib` is consumed exclusively via `uv add --dev --editable ../lib` — confirmed in `pyproject.toml`'s `[tool.uv.sources]` / `[dependency-groups]` and `uv.lock`. No files copied from `lib`.
- [x] `lib/pyproject.toml`'s packaging fix (added `[build-system]`, `core`/`config`/`models` exposed as top-level packages, `project_root.py` included) is exercised by real imports throughout the test suite (e.g. `tests/unit/test_pipeline_tracks.py`, `tests/integration/test_real_pipeline.py`).
- [x] Ruff and mypy run clean, both locally and via `.github/workflows/heatmaps-backend-ci.yml`.
- [x] Pytest suite includes unit tests for pipeline stages (with `lib` calls mocked/stubbed — see `tests/unit/test_pipeline_tracks.py`, `tests/unit/test_worker_tasks.py`) and one integration test (`tests/integration/test_real_pipeline.py`) that runs a few frames of a real sample video through the actual pipeline.
- [x] No bare `except:`/`except Exception: pass` — the two `except Exception` sites (`app/api/routes/health.py`, `app/worker/tasks.py`) both log and act on the error rather than swallowing it.
- [x] Logging is correlated by `job_id` on the failure path (`logger.exception("job %s failed", job_id)` in `app/worker/tasks.py`); not extensively instrumented elsewhere (e.g. no per-request structured logging in the upload route beyond uvicorn's own access log) — acceptable for v1, worth revisiting if debugging production issues proves hard without it.

## Configuration & security

- [x] All environment-specific values come from `pydantic-settings`/env vars (`app/config.py`) — no hardcoded paths, ports, or secrets in code.
- [x] Uploaded files and job output directories are named by server-generated UUID (`job_id`); upload filenames are never used for storage paths (fixed `source.<sniffed-ext>`). `StaticFiles` provides the traversal guard for the `/media/{job_id}/{heatmap_type}` route.
- [x] CORS is restricted to the configured frontend origin(s) (`cors_origins` setting, default `http://localhost:5173`), not `*`.
- [x] `/health` reflects real Redis connectivity — verified manually with Redis both up (`200`) and down (`503`) — and also reports `workers_online`/`queued_jobs`, verified manually showing `workers_online: 0` while a real upload sat stuck at `queued`, and `workers_online: 1` with the same job draining and completing once a worker started.

## Operations

- [ ] `docker-compose up` brings up `redis`, `api`, and `worker` together with one command. `docker-compose.yml`/`Dockerfile` are written (context set to the parent directory so `../lib`'s source is available in the image; `ffmpeg`/`libgl1` installed; worker uses `SimpleWorker`) but **not actually run** — no Docker available in the environment this was built in. Treat as unverified until someone runs it for real.
- [x] Retention/cleanup policy for `data/uploads` and `data/jobs` is documented in the README ("Known v1 limitations": kept indefinitely, no automated cleanup yet).
- [x] Known v1 limitations are written down in the README: Redis as sole job-state store, single sequential worker, `directional`/`speed`/`cluster` only, `YOLOModel` only, real-world speed accuracy bounded by `CameraInfo`'s fixed calibration, unbounded `data/` growth.

## Found during implementation (not pre-existing knowledge)

- `lib/core/momentum/momentum.py`'s `MomentumTracker.update_batch` has a real bug in its no-`CameraToWorldMapper` branch (a 3-tuple unpack against a 2-element `zip` — crashes unconditionally if hit). Not fixed, and not hit: by product decision `pipeline.py` always constructs a `CameraToWorldMapper` from `CameraInfo`'s transformation matrix and passes it in, so that branch is dead code for this backend. `lib/core/momentum/` is otherwise untouched.
- RQ's default fork-per-job `Worker` crashes on macOS dev machines (Objective-C fork-safety abort — triggered by torch/opencv's ObjC-linked bits). Switched to `rq.worker.SimpleWorker` everywhere (dev instructions, `docker-compose.yml`), which also happens to match this project's documented single-sequential-worker design.
- Reported symptom: frontend progress bar stuck at 0% forever. Root cause, confirmed live: no `rq worker` process was running, so the job sat `queued` indefinitely with zero feedback anywhere. `POST /api/upload` and the `queued`/`processing` states give no signal that nothing is consuming the queue. Fixed by adding `workers_online`/`queued_jobs` to `GET /health` (see `api-contract.md`) so this is diagnosable instead of silent. This is a real, easy-to-hit gap in the local two-terminal dev workflow (`uvicorn` in one, `rq worker` in another — trivial to start only the first); `docker-compose up` doesn't have this problem since it always starts both.
