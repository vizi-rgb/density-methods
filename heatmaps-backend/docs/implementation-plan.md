# Implementation Plan — heatmaps-backend

## Context

`heatmaps-backend` is currently a bare `uv init` FastAPI stub: `pyproject.toml` declares only `fastapi[standard]`, `main.py` is the default uv template, `docs/` is empty. It needs to become the service that sits between `heatmaps-frontend` and the `../lib` (density-methods) crowd-analysis library:

1. Accept an uploaded video from the frontend.
2. Run it through `lib` to produce one or more heatmap-overlay videos.
3. Package each output as HLS (`.m3u8` + segments) so the frontend can play it with `hls.js`.
4. Report job progress back to the frontend in real time (SSE), matching the flow already assumed in `heatmaps-frontend/docs/frontend-plan.md` (`IDLE → UPLOADING → PROCESSING → READY_TO_PLAY`).

`lib` is a sibling uv project, not a subdirectory of this repo — it must be consumed as a **dev dependency** (`uv add --dev --editable ../lib`), never copied into this repo.

### What `lib` gives us today

`lib/main.py` is a hand-wired script, not a reusable pipeline:

```
YOLOModel(weights).run_tracking(stream=True)          # generator of ultralytics Results
  -> StreamedPredictionsAdapterFactory.for_model(model)  # Results -> Prediction/Point domain objects
  -> MomentumTracker.update_batch(track_ids, points)     # -> list[TrackUpdate] (direction, speed)
  -> heatmap_builder.handle(track_updates)               # per selected heatmap type
  -> HeatmapVisualizer.draw(heatmap, frame, save_path)   # overlay -> np.ndarray, optionally saved as PNG
```

Five heatmap types exist as Builder-pattern classes under `lib/core/heatmap/`:

| Type | Builder | Extra input needed |
|---|---|---|
| `directional` | `DirectionalHeatmap` (`core/heatmap/directional/`) | none |
| `speed` | `SpeedHeatmap` + `SpeedFilter` (`core/heatmap/speed/`) | none (default filter) |
| `cluster` | `ClusterHeatmap` (`core/heatmap/clusters/`) | none |
| `roi` | `RoiHeatmap` (`core/heatmap/roi/`) | polygon (`with_polygon`) |
| `tripwire` | `TripwireHeatmap` (`core/heatmap/tripwire/`) | line + inside point (`with_tripwire`) |

Neither the backend nor the frontend collects polygon/line geometry today, so **v1 supports only `directional`, `speed`, and `cluster`**. `roi`/`tripwire` are a documented non-goal until a geometry-input UI exists.

There is no single `run(video_path) -> result` entrypoint in `lib` — the backend must build its own orchestration wrapper reusing the pieces above. Model support is also asymmetric: `YOLOModel.run_tracking()` works; `YOLOCrowdModel.run_tracking()` raises `NotImplementedError` and has no adapter — **v1 uses `YOLOModel` only**.

### Prerequisite: fix `lib`'s packaging

`lib/pyproject.toml` has no `[build-system]` table, and `core`/`config`/`models` are flat top-level modules (no namespace package, no `src/` layout). As-is, `uv add --dev --editable ../lib` will not produce anything importable. In scope for this work:

- Add a `[build-system]` table to `lib/pyproject.toml` (hatchling) and package metadata so `core`, `config`, `models`, `project_root` are importable as a real package (e.g. `density_methods.core...`).
- Verify `lib`'s config/weight loading (`project_root.py`, `config/config.yaml`) still resolves correctly when imported from a different process working directory (`heatmaps-backend`), not just when run from `lib/` — this is a real risk since paths are currently resolved relative to a `PROJECT_ROOT` computed at import time.
- Smoke test: from `heatmaps-backend`, `import density_methods.core.heatmap...` and instantiate one builder successfully.

This is a small, low-risk change to `lib`'s packaging metadata only — no behavioral changes to its analysis logic.

## Target repo layout

```
heatmaps-backend/
  app/
    main.py                    # FastAPI app factory, mounts routers + static files
    config.py                  # pydantic-settings: REDIS_URL, DATA_DIR, MAX_UPLOAD_MB,
                                #   ALLOWED_HEATMAP_TYPES, CORS_ORIGINS, HLS_SEGMENT_SECONDS
    api/
      routes/
        upload.py               # POST /api/upload
        status.py               # GET /api/status/{id}, GET /api/status/{id}/stream (SSE)
        health.py                # GET /health
      schemas.py                 # pydantic request/response models (see api-contract.md)
    domain/
      job.py                     # JobStatus enum, Job model (id, status, types, progress, outputs, error)
    services/
      pipeline.py                # orchestrates lib: model -> adapter -> momentum -> builders -> visualizer
      hls_encoder.py             # ffmpeg subprocess wrapper: frames -> HLS per type
      storage.py                 # path helpers for uploads/jobs/hls dirs, static mount config
    worker/
      tasks.py                   # RQ job function: process_video(job_id)
      queue.py                   # RQ Queue + Redis connection setup
  data/                          # gitignored: uploads/{job_id}/source.mp4, jobs/{job_id}/hls/{type}/
  docker-compose.yml             # redis, api (uvicorn), worker (rq worker)
  Dockerfile
  tests/
    unit/
    integration/
  docs/
    implementation-plan.md
    api-contract.md
    acceptance-criteria.md
```

## Pipeline design (`services/pipeline.py`)

One video decode pass per job, fanned out to the selected heatmap types:

1. `DataSourceInfoReader(video_path).read()` → `DataSourceInfo(height, width, frames, fps)` — used for progress % and for sizing the ffmpeg `rawvideo` pipes.
2. `YOLOModel(weights_path).run_tracking(stream=True)` → generator of ultralytics `Results`, one per frame.
3. `StreamedPredictionsAdapterFactory.for_model(model)` adapts each `Results` into internal `Prediction`/`Point` objects.
4. `MomentumTracker(fps, momentum_buffer_size, max_lost_frames).update_batch(track_ids, points)` → `list[TrackUpdate]` (adds direction/speed).
5. For each *selected* type, one builder instance built once at job start (`DirectionalHeatmapBuilder().with_height/width/frames/fps(...).build()`, etc.), fed the same `TrackUpdate` list every frame via `.handle(...)`.
6. Per type per frame: `HeatmapVisualizer(fixed_max, alpha, sigma).draw(heatmap, frame, save_path=None)` → in-memory `np.ndarray` (BGR overlay). **No per-frame PNGs are written to disk** — this is the one deliberate deviation from `lib/main.py`'s pattern, to avoid the I/O overhead of writing/reading thousands of PNGs per job.
7. Each type's frame array is written directly to that type's own `ffmpeg` subprocess via a `rawvideo` stdin pipe (see below) — so N heatmap types run N concurrent encoders fed from the single decode+inference pass.
8. Every ~1% of frames processed (or every N frames), the worker updates job progress (see Job queue section).

## HLS encoding (`services/hls_encoder.py`)

One `ffmpeg` subprocess per heatmap type, started when the job begins processing:

```
ffmpeg -f rawvideo -pix_fmt bgr24 -s {width}x{height} -r {fps} -i pipe:0 \
  -c:v libx264 -pix_fmt yuv420p \
  -f hls -hls_time {HLS_SEGMENT_SECONDS} -hls_playlist_type vod \
  -hls_segment_filename "{job_dir}/{type}/segment_%03d.ts" \
  "{job_dir}/{type}/stream.m3u8"
```

Frame arrays are written to the subprocess's stdin as raw bytes as they're produced by step 6 above; stdin is closed and the process is waited on when the frame stream ends. `hls_playlist_type vod` works correctly with a streamed/piped input — ffmpeg finalizes the playlist on EOF. This avoids double-encoding (no intermediate MP4) and avoids ever writing individual overlay frames as image files.

## Job queue: Redis + RQ

- `POST /api/upload` saves the file, creates a `Job` record, and enqueues `process_video(job_id)` onto an RQ queue.
- A separate `worker` process/container runs `rq worker` and executes `process_video`.
- Job status/progress is stored in the RQ job's `meta` dict, updated by the worker as frames are processed (`job.meta["progress"] = pct; job.save_meta()`), plus a `status` field (`queued` → `processing` → `completed`/`failed`) and, on completion, an `outputs` array of `{type, label, manifest_url}` — one entry per selected heatmap type.
- Redis is the **single source of truth** for job state in v1 — no separate database. Documented limitation: job history is lost if Redis data expires or is flushed; acceptable for v1, revisit if job history/audit becomes a requirement.
- RQ chosen over Celery: this is a single queue of CPU/GPU-bound jobs with no need for scheduling, routing, or multi-broker support — RQ's simpler operational footprint (no separate scheduler/beat process) fits better. Revisit if multi-queue priority or retry/backoff policies become necessary.

## SSE status endpoint

`GET /api/status/{job_id}/stream` opens a `text/event-stream` response that polls the RQ job's status/meta from Redis (e.g. every 1s) and yields an event each time status or progress changes, until a terminal state (`completed`/`failed`) is reached, then closes the stream. See `api-contract.md` for exact payload shapes.

## Docker Compose

Three services sharing a `data/` volume:

- `redis` — job queue broker/state store.
- `api` — `uvicorn app.main:app`, handles HTTP/SSE, enqueues jobs, serves HLS output via `StaticFiles`.
- `worker` — `rq worker`, runs `services.pipeline` + `services.hls_encoder` per job. Single worker process in v1 (jobs processed sequentially) since inference is CPU/GPU heavy and contention between concurrent jobs would degrade both.

## Frontend contract impact

`heatmaps-frontend` already implements the `outputs[]`/`/api/status/{job_id}/stream` shape this plan uses (see `heatmaps-frontend/docs/api-integration.md`), so no frontend rework is needed for that part. The one real gap: **its upload flow has no `heatmap_types` selection UI yet** — `FileUpload.tsx`/`client.ts` only send `file`. That's a required frontend-side addition, spelled out precisely in `api-contract.md` and `heatmaps-frontend/docs/api-integration.md`'s "current implementation gaps" section.

## Build phases

0. **lib packaging fix** — add `[build-system]` to `lib/pyproject.toml`, confirm `uv add --dev --editable ../lib` + `import density_methods...` works from `heatmaps-backend`.
1. **Backend skeleton** — `app/` structure, `config.py`, `docker-compose.yml` (api+worker+redis), `/health`, CI (lint/type/test) scaffolding.
2. **Upload + job plumbing** — upload endpoint, storage paths, `Job` model, RQ queue wiring, a no-op/fake worker (sleeps + fake progress) to prove the full loop (upload → queue → status → completion) before wiring real ML.
3. **Real pipeline integration** — swap the fake worker for the real `services/pipeline.py` (model, adapter, momentum tracker, selected builders).
4. **HLS encoding** — `services/hls_encoder.py` wired into the pipeline, static file serving, manifest URLs in job output.
5. **SSE** — `GET /api/status/{job_id}/stream` replacing/augmenting polling, backed by RQ job meta.
6. **Hardening** — input validation, error handling/failure states, retention/cleanup of `data/`, CORS, full test suite, README/docs pass, load smoke test with concurrent uploads.
