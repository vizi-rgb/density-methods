# Acceptance Criteria — heatmaps-backend

Definition-of-Done for the incremental-per-heatmap / MP4 redesign (see `implementation-plan.md`). Checked items were actually verified (live upload+processing through a real worker + `ffprobe`, or an automated test), not just implemented-and-assumed-correct.

## Functional

- [x] `POST /api/videos` accepts a valid video, stores it, returns `video_id` + a directly-playable `video_url` for the raw upload — no job created. Verified live + `tests/integration/test_videos_and_heatmaps_flow.py`.
- [x] `POST /api/videos/{id}/heatmaps` with a valid `directional`/`speed`/`cluster` body creates a job that reaches `completed` with a single, independently playable MP4 `output.video_url`. Verified live for **all three types** against a real video: `ffprobe`-checked (h264, correct dims/fps/duration, moov atom before mdat i.e. faststart worked) and visually confirmed — a `direction: "right"` request renders only the one rightward-moving trail, not every direction (proving the parameter is actually applied, not just plumbed through).
- [x] Invalid `direction`, `group_size < 2`, or `min_speed > max_speed` → `400 invalid_request`, no job created. Unknown `video_id` → `404 video_not_found`. Covered by `tests/integration/test_videos_and_heatmaps_flow.py`.
- [x] Non-video file / oversized file → `415`/`413`, no video stored. Covered by the same test file.
- [x] A mid-job pipeline failure reaches `failed` with a descriptive `error`, and the ffmpeg encoder is killed rather than left running. Covered by `tests/unit/test_worker_tasks.py`. Not separately tested: a genuinely corrupt input file reaching this path (only a synthetic pipeline exception was tested) — `pipeline.read_metadata`'s fps/frame-count checks are the intended guard there.
- [x] Progress is monotonically non-decreasing, reaches 100 only at `completed` (capped at 99 while processing) — observed live and covered by `tests/unit/test_worker_tasks.py`.
- [x] `GET /api/heatmaps/{job_id}` returns correct state after an SSE disconnect/reload — covered by `tests/integration/test_videos_and_heatmaps_flow.py`; exercised manually polling a real job to completion.
- [x] Cluster `group_size` is an **exact** match (not "N or more") — `tests/unit/test_pipeline_tracks.py::test_cluster_track_renders_only_the_requested_group_size` asserts a size-3 request stays empty when only a size-2 cluster actually formed.
- [ ] Multiple jobs against the same video, or multiple videos, processed concurrently without cross-job/cross-video leakage — not tested with genuine concurrency (same gap as before this redesign; UUID-per-resource + no shared mutable state supports it, but it's reasoning, not a verified guarantee).
- [x] Only `lib`'s `YOLOModel` is used — true by construction.

## Code quality

- [x] `lib` consumed exclusively via `uv add --dev --editable ../lib`; `lib/core/momentum/` is untouched — `pipeline.py` always supplies a `CameraToWorldMapper` so the (real, pre-existing) bug in `momentum.py`'s no-mapper branch is never hit, by design, without patching `lib`.
- [x] Ruff and mypy clean, locally and via `.github/workflows/heatmaps-backend-ci.yml`.
- [x] Pytest: unit tests for each track type's parameter handling and the worker task's success/failure paths (mocked `lib`/encoder), plus a real-video integration test parametrized over all three heatmap types.
- [x] No bare `except:`/`except Exception: pass` — the two `except Exception` sites (`health.py`, `worker/tasks.py`) both log and act.
- [x] Failure logging includes `job_id` (`logger.exception("job %s failed", job_id)`).

## Configuration & security

- [x] Config via `pydantic-settings`/env vars only.
- [x] `video_id`/`job_id` are server-generated UUIDs; storage paths never derive from client input (fixed `source.<sniffed-ext>` / `output.mp4`). `StaticFiles` guards the `/media/*` routes.
- [x] CORS restricted to the configured frontend origin(s), not `*`.
- [x] `/health` reflects real Redis connectivity + `workers_online`/`queued_jobs` — verified live in both the "worker running" and "worker down, job stuck queued" states.

## Operations

- [ ] `docker-compose up` brings up `redis`/`api`/`worker` together — written (context set to the parent dir so `../lib` is available in the image) but **not run** in this environment (no Docker available). Still unverified; re-check before relying on it.
- [x] Known v1 limitations documented in the README: Redis as sole job-state store, single sequential worker, `directional`/`speed`/`cluster` only (no `roi`/`tripwire`), speed accuracy bounded by `CameraInfo`'s fixed calibration, no video dedup, unbounded `data/` growth.

## Found during this redesign

- Dropping HLS for plain MP4 removed `hls_encoder.py`'s HLS-specific ffmpeg flags (segment filename, `-hls_time`, GOP tuning) entirely — `mp4_encoder.py` is meaningfully simpler, one output file instead of a manifest + N segments.
- The old `outputs: array` shape (one job → many types) is gone; `output` is now singular (one job → one type+params → one result), which is a real, load-bearing simplification now that each "Add" in the frontend is its own independent job.
