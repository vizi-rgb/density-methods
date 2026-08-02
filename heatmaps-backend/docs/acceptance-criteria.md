# Acceptance Criteria — heatmaps-backend

Definition-of-Done checklist for the v1 backend described in `implementation-plan.md` / `api-contract.md`. A change is not "done" until every applicable item below is checked.

## Functional

- [ ] Uploading a valid video with a valid `heatmap_types` selection produces a job that reaches `completed`, with one independently playable HLS manifest per selected type (verified with `ffprobe` and/or a real `hls.js` playback smoke test, not just "file exists").
- [ ] Selecting `roi` or `tripwire` (or any unknown type), or an empty `heatmap_types`, is rejected at upload time with `422` — no job is created.
- [ ] Uploading a non-video file, or a file exceeding `MAX_UPLOAD_MB`, is rejected (`415`/`413`) — no job is created. Validation checks actual file content (magic bytes), not just filename extension or client-supplied content-type header.
- [ ] A corrupt video, an unsupported codec, or a mid-job model/ffmpeg failure causes the job to reach `failed` with a descriptive `error` message — never a stuck `processing` state, and no orphaned ffmpeg or worker processes left running.
- [ ] Progress reported via SSE/`GET /api/status/{id}` is monotonically non-decreasing and only reaches 100 at `completed`.
- [ ] After an SSE disconnect or a frontend page reload mid-job, `GET /api/status/{job_id}` returns the correct current state (frontend can resume without re-uploading).
- [ ] Multiple jobs uploaded concurrently are all accepted, queue correctly, and are processed without cross-job state leakage (no job's output ends up in another job's directory/manifest).
- [ ] `lib`'s `YOLOModel` path (not `YOLOCrowdModel`, which lacks tracking support) is the one used; this is a known v1 constraint, not silently broken behavior.

## Code quality

- [ ] `lib` is consumed exclusively via `uv add --dev --editable ../lib` (verify in `pyproject.toml`/`uv.lock`) — no files copied or duplicated from `lib` into this repo.
- [ ] `lib/pyproject.toml`'s packaging fix (added `[build-system]`) is verified by an actual `import density_methods...` in this repo's test suite, not just by manual `uv add` succeeding once.
- [ ] Ruff and mypy run clean in CI.
- [ ] Pytest suite includes unit tests for pipeline stages (with `lib` calls mockable/stubbed) and at least one integration test that runs a short real sample video end-to-end through the actual pipeline and asserts a valid HLS manifest is produced.
- [ ] No bare `except:`/`except Exception: pass` swallowing errors; failures are logged with enough context to diagnose (`job_id`, stage, underlying exception).
- [ ] Logging is structured and correlated by `job_id` throughout the upload → queue → pipeline → encode path.

## Configuration & security

- [ ] All environment-specific values (Redis URL, data directory, upload size limit, allowed heatmap types, CORS origins, HLS segment length) come from `pydantic-settings`/env vars — no hardcoded paths, ports, or secrets in code.
- [ ] Uploaded files and job output directories are named by server-generated UUID (`job_id`), never derived from client-supplied filenames — no path traversal possible via upload filename or the `{job_id}`/`{heatmap_type}` static-media route.
- [ ] CORS is restricted to the configured frontend origin(s), not `*`.
- [ ] `/health` reflects real dependency state (actual Redis ping), not a hardcoded `200`.

## Operations

- [ ] `docker-compose up` brings up `redis`, `api`, and `worker` together with one command, using a shared `data/` volume; documented in the backend README.
- [ ] Retention/cleanup policy for `data/uploads` and `data/jobs/*/hls` is documented (even if v1's policy is "manual/unbounded for now") so disk growth is a known, tracked limitation rather than a surprise.
- [ ] Known v1 limitations are written down where a future reader will find them (not just in this doc): Redis as sole job-state store (history lost on flush/expiry), single sequential worker (no concurrent job processing), no `roi`/`tripwire` support, `YOLOModel` only.
