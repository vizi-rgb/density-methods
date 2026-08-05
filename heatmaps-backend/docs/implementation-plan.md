# Implementation Plan — heatmaps-backend

## Context

Second-generation design. The first version let the frontend select 1+ heatmap types at upload time, ran them all together in one job, and served each as an HLS stream. The actual product need turned out to be different: **upload a video once, then incrementally add any number of individual, parameterized heatmap analyses to it** — pick a direction, or a speed range, or an exact group size — each producing its own independent, playable result. HLS was also dropped: it was adopted for adaptive/progressive-streaming benefits this app never uses (one fixed quality, self-hosted, and the frontend never gets a URL before a job is `completed` anyway) — so every video (the raw upload preview *and* every heatmap result) is now a plain MP4 (`-movflags +faststart` for seekability), played with a plain `<video>` tag. No `hls.js` anywhere.

### What `lib` gives us for the three parameterized types

- **Directional**: `DirectionalHeatmap.get_heatmap()` returns a dict with keys `all`/`static`/`up`/`down`/`left`/`right` — pick exactly one.
- **Speed**: `SpeedHeatmapBuilder.with_speed_filter(SpeedFilter(...))` takes `min_speed`/`max_speed` bounds and a `get_speed_function`. We use `speed_km_per_h` (see camera-calibration note below), with a single filter built from whatever bounds the request gives (missing bound → `0`/`inf`).
- **Cluster**: `ClusterHeatmap.get_heatmap()` buckets by **exact** DBSCAN cluster size as dynamic string keys (`"2"`, `"3"`, ...) — a request for group size N reads that one bucket (or an empty frame if it never occurs that video).

**Always uses `CameraToWorldMapper(CameraInfo().get_transformation_matrix())`** for `MomentumTracker` (product decision, unrelated to this redesign) — `CameraInfo`'s calibration keypoints are hardcoded to one specific reference video, so `speed_km_per_h` accuracy for other footage is bounded by how close that calibration happens to be. `lib/core/momentum/` itself is never modified — this is passed in from `pipeline.py`, not changed in `lib`.

Neither `directional`/`speed`/`cluster` needs geometry input; `roi`/`tripwire` (which do — a polygon/tripwire line) are still out of scope, no UI for it.

## Target repo layout

```
heatmaps-backend/
  app/
    main.py                    # FastAPI app factory; mounts /media at data_dir (covers videos/ and jobs/)
    config.py                  # pydantic-settings
    api/
      routes/
        videos.py               # POST /api/videos
        heatmaps.py              # POST /api/videos/{id}/heatmaps, GET /api/heatmaps/{id}(/stream)
        health.py                 # GET /health
      schemas.py                  # VideoUploadResponse, HeatmapJobResponse, discriminated HeatmapRequest union
    domain/
      job.py                       # JobStatus/JobState/VideoOutput, build_label()
    services/
      pipeline.py                  # lib orchestration: model -> adapter -> momentum -> ONE track -> visualizer
      mp4_encoder.py                 # ffmpeg subprocess: rawvideo stdin -> single MP4 file
      storage.py                     # video/job path helpers, URL building
    worker/
      tasks.py, queue.py
  data/                          # gitignored: videos/{video_id}/source.<ext>, jobs/{job_id}/output.mp4
  docker-compose.yml, Dockerfile
  tests/unit/, tests/integration/
```

## Storage layout

`data/videos/{video_id}/source.<ext>` — one raw upload per `video_id` (plain `uuid4()`, no content-hash dedup — considered, explicitly out of scope). `data/jobs/{job_id}/output.mp4` — one file per heatmap job. A single `StaticFiles` mount at `/media` covers `data_dir` itself (both trees), so `GET /media/videos/{id}/source.<ext>` and `GET /media/jobs/{id}/output.mp4` need no special-casing in `main.py`.

## Pipeline design (`services/pipeline.py`)

One video decode + YOLO tracking pass per job, feeding exactly **one** heatmap track (not N, unlike the first design):

1. `DataSourceInfoReader` → `DataSourceInfo` (progress % denominator, ffmpeg frame size).
2. `YOLOModel(...).run_tracking(stream=True)` → `StreamedPredictionsAdapterFactory` → `MomentumTracker.update_batch()` (with the always-on `CameraToWorldMapper`).
3. A single track object built from the request: `_DirectionalTrack(direction)`, `_SpeedTrack(min_speed, max_speed)`, or `_ClusterTrack(group_size)` — each just wraps the matching `lib` builder and exposes `.frame()` returning the one relevant 2D array (fixed key for directional/speed, exact-match dynamic key for cluster).
4. `HeatmapVisualizer.draw(track.frame(), frame)` → one BGR overlay `np.ndarray` per input frame, yielded directly (no dict of types, no per-frame file I/O).

## MP4 encoding (`services/mp4_encoder.py`)

One `ffmpeg` subprocess per job, frames piped into `stdin` as `rawvideo` (`bgr24`) as they're produced:

```
ffmpeg -y -loglevel error -f rawvideo -pix_fmt bgr24 -s {w}x{h} -r {fps} -i pipe:0 \
  -an -c:v libx264 -pix_fmt yuv420p -movflags +faststart {output_path}
```

Same stderr-draining-thread design as before (still needed — same pipe-deadlock risk when streaming large amounts of raw video into `stdin` while ffmpeg logs to `stderr`). No manifest, no segments — `close()` just waits for one file to finish encoding.

## Job queue: Redis + RQ (unchanged)

`POST /api/videos/{id}/heatmaps` enqueues `process_video(job_id, video_path, heatmap_request, base_url)`. Job status/progress/output/error live in the RQ job's `meta`, read via `JobState.from_rq_job`. **Always run the worker as `rq worker --worker-class rq.worker.SimpleWorker video-processing`** — RQ's default fork-per-job worker crashes on macOS (Objective-C fork-safety abort, torch/opencv) and `SimpleWorker` also matches the single-sequential-worker v1 design. `GET /health` reports `workers_online`/`queued_jobs` so "no worker running" (jobs stuck `queued` forever, zero other symptom) is diagnosable instead of silent.

## Build phases (this redesign)

0. ~~Storage layout + path helpers~~ — done.
1. ~~Schemas (discriminated request union) + domain (`JobState.output` singular, `build_label`)~~ — done.
2. ~~`pipeline.py` single-track rewrite~~ — done, verified against real video for all three types.
3. ~~`mp4_encoder.py` replacing `hls_encoder.py`~~ — done.
4. ~~`worker/tasks.py` single-output rewrite~~ — done.
5. ~~Routes (`videos.py`, `heatmaps.py`) + `main.py` wiring~~ — done, verified live end-to-end (upload → 3 parallel-type jobs → real MP4 output, `ffprobe`-checked, visually confirmed the directional filter actually isolates one direction).
6. ~~Tests rewritten for the new shapes~~ — done, `ruff`/`mypy`/`pytest` (incl. `-m integration`, all 3 types) clean.
7. Docs (this pass) + frontend rework (`heatmaps-frontend`, tracked separately).
