# AGENTS.md — heatmaps-backend

FastAPI service: upload a video once, then incrementally add independent,
parameterized heatmap analyses (directional/speed/cluster/tripwire/roi)
against it, analyzed with the sibling `../lib` (`density-methods`) library.
Every result is a plain MP4 (no HLS/`hls.js`) for `heatmaps-frontend` to play.

Full design docs — read these before making non-trivial changes:
- [`docs/implementation-plan.md`](docs/implementation-plan.md) — architecture, why MP4 not HLS, pipeline design.
- [`docs/api-contract.md`](docs/api-contract.md) — authoritative wire contract with the frontend.
- [`docs/acceptance-criteria.md`](docs/acceptance-criteria.md) — Definition of Done, what's actually verified vs. assumed.
- [`README.md`](README.md) — setup/run/test commands, known v1 limitations.

## Stack

Python 3.13, `uv`, FastAPI, Redis + RQ (job queue), `ffmpeg` (subprocess, MP4
encoding — plain rawvideo-stdin → `libx264` + `-movflags +faststart`, no HLS
muxing), `pydantic-settings` (config). `lib` (`density-methods`) is a
sibling uv project consumed as an **editable dev dependency**
(`[tool.uv.sources]` in `pyproject.toml`) — never copy its files into this
repo. It provides YOLO tracking + heatmap builders; there's no single
video-in/heatmap-out entrypoint in `lib` itself — `app/services/pipeline.py`
is the orchestration wrapper.

## Layout

```
app/
  main.py              # FastAPI app factory; mounts /media at data_dir (covers videos/ + jobs/)
  config.py             # pydantic-settings
  api/routes/
    videos.py             # POST /api/videos
    heatmaps.py            # POST /api/videos/{id}/heatmaps, GET /api/heatmaps/{id}(/stream)
    health.py
  api/schemas.py, errors.py   # schemas.py has the discriminated HeatmapRequest union
  domain/job.py          # JobStatus/JobState (output is SINGULAR), build_label()
  services/pipeline.py    # lib orchestration for exactly ONE heatmap request -> ONE frame stream
  services/mp4_encoder.py   # ffmpeg subprocess: rawvideo stdin -> one MP4 file
  services/storage.py       # video/job path helpers, URL building
  worker/queue.py, tasks.py
tests/unit/, tests/integration/
```

## Commands

```bash
uv sync
redis-server --daemonize yes                                   # or: docker compose up -d redis
uv run uvicorn app.main:app --reload                            # terminal 1
uv run rq worker --worker-class rq.worker.SimpleWorker video-processing   # terminal 2 — see gotcha below

uv run pytest -m "not integration"   # fast: unit + HTTP wiring (fakeredis)
uv run pytest -m integration         # slow: real YOLO pipeline, all 5 types, needs lib's weights+sample video
uv run ruff check .
uv run mypy app tests
```

CI (`.github/workflows/heatmaps-backend-ci.yml`, at repo root — this is a
monorepo) runs ruff/mypy/`pytest -m "not integration"` on push/PR touching
`heatmaps-backend/` or `lib/`.

## Non-obvious things worth knowing before touching this code

- **One job = one heatmap type + params = one MP4.** This is the second
  design of this backend. The first let you select multiple heatmap types
  at upload and got an array of outputs back from one job; that's gone.
  `POST /api/videos` only stores the video; `POST /api/videos/{id}/heatmaps`
  is what creates a job, one per call, and `JobState.output`/`job.meta["output"]`
  are **singular**, not a list. If you're tempted to batch multiple types
  into one job again, don't — the frontend's whole UX (add tiles one at a
  time to a grid) depends on each job being independent.
- **No HLS, anywhere, on purpose.** Dropped deliberately: HLS's real
  benefits (adaptive bitrate, progressive playback, CDN segment caching)
  aren't used by this app — one fixed quality, self-hosted, and the
  frontend never gets a URL before a job is `completed` anyway, so there
  was never any progressive-streaming benefit being captured. Everything is
  a single MP4 with `-movflags +faststart`. Don't reintroduce
  `hls_encoder.py`/segment logic without a real reason (e.g. wanting to
  show a video *while it's still processing*, which would need other
  changes too, not just switching the container format back).
- **`_ClusterTrack` does exact-match, not "N or more."** `group_size: 3`
  renders only frames where DBSCAN found a cluster of exactly 3 — confirmed
  with the user, not a guess. `lib`'s `ClusterHeatmap.get_heatmap()` buckets
  are dynamic string keys (`"2"`, `"3"`, ...) per distinct size seen; the
  track just reads `buckets.get(str(group_size))`, empty frame if that
  exact size never occurs.
- **`_DirectionalTrack`/`_SpeedTrack` read one specific sub-key now**, not
  an aggregate. Directional: `get_heatmap()[direction]` (one of `all`/
  `static`/`up`/`down`/`left`/`right`, whichever the request asked for).
  Speed: one `SpeedFilter` built from the request's `min_speed`/`max_speed`
  (missing bound → `0`/`inf`), keyed off `speed_km_per_h`.
- **`tripwire` is a special case of `roi`, not a separate analysis.**
  `lib`'s `TripwireHeatmap` computes a half-plane polygon from the request's
  `p1`/`p2`/`inside_point` (extends the line to the image borders) and
  delegates everything to an internal `RoiHeatmap`. Both `_TripwireTrack`
  and `_RoiTrack` (`app/services/pipeline.py`) read one of the same 4 bucket
  keys off `get_heatmap()` — `inside`/`outside`/`inside->outside`/
  `outside->inside` — selected by the request's `bucket` field
  (`RegionBucket` in `schemas.py`). `_TripwireTrack.draw()`/`_RoiTrack.draw()`
  first render the background via the plain `HeatmapVisualizer`, then draw
  their shape on top of that with a separate draw-only visualizer —
  `TripwireVisualizer` (a line, using `get_tripwire()`'s *border-extended*
  endpoints, not the raw clicked `p1`/`p2`) or `RoiVisualizer` (a closed
  polygon). Those two classes (`core/heatmap/visualizer/tripwire_visualizer.py`,
  `.../roi_visualizer.py`) only draw their shape onto an already-rendered
  image — they don't know about `HeatmapVisualizer` or heatmaps at all,
  which is what lets multiple regions be drawn onto one background in a
  chain. Both tracks' `flush()` is a no-op — the underlying
  `RoiHeatmap.execute_track_update_batch()` raises `NotImplementedError` for
  lost-track flushing, so it must never be called for these two types.
- **`lib/core/momentum/` stays unchanged — by explicit product decision.**
  `MomentumTracker.update_batch`'s no-mapper branch has a real bug (crashes
  unconditionally — a 3-tuple unpack against a 2-element `zip`), but it's
  never exercised because `pipeline.py` always builds and passes a
  `CameraToWorldMapper`. Don't "fix" it in `lib` — if you ever need the
  no-mapper path, handle it without touching `lib`, or raise it with
  whoever owns `lib`.
- **`CameraInfo`'s calibration is for one specific reference video.**
  `speed_km_per_h` accuracy for other footage is only as good as that fixed
  calibration happens to be for it. Known, accepted limitation, not a bug.
- **"Upload/job-creation succeeds but progress bar is stuck at 0%" almost
  always means no `rq worker` process is running.** Confirmed live in the
  previous design and still true here — a job sits `queued` forever with
  zero other symptom. Check `GET /health` — `workers_online: 0` with
  `queued_jobs > 0` is the exact signature.
- **Always use `--worker-class rq.worker.SimpleWorker`.** RQ's default
  fork-per-job worker crashes on macOS (`objc[...]: +[NSNumber initialize]
  may have been in progress...`) because torch/opencv link Objective-C
  runtime bits that aren't fork-safe. `SimpleWorker` also matches this
  project's documented single-sequential-worker design. `docker-compose.yml`
  already uses it.
- **`lib` is only pip-installable at all because of a packaging fix** in
  `lib/pyproject.toml` (`[build-system]` + `packages = ["core", "config",
  "models"]` + `include = ["project_root.py"]`). `lib`'s modules use bare
  absolute imports (`from core.heatmap... import`, `from project_root import
  PROJECT_ROOT`) rather than a `density_methods` namespace — that's why it's
  exposed as three top-level packages instead of one.
- **`density-methods` is a *dev* dependency but a real *runtime*
  dependency of the worker.** Don't add `--no-dev` to `uv sync` in the
  Dockerfile.
- **`docker-compose.yml`'s build `context` is the parent directory**
  (`..`, i.e. `density-methods/`) — the image needs `../lib`'s source
  alongside this project's. Not verified by an actual `docker compose
  build` run (no Docker in the environment this was built in).
- **Weight files and the sample video are gitignored** in `lib/` — present
  locally if `lib` is already set up, absent on a fresh clone/in CI. That's
  why the real-pipeline integration test is excluded from CI.
- **No content-hash video dedup.** Considered, explicitly decided against
  for this pass — re-uploading identical bytes creates a new `video_id` and
  a new copy on disk. If this ever gets revisited, remember `video_id` is
  currently a plain `uuid4()`, not a hash.
