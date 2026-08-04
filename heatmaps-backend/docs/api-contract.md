# API Contract — heatmaps-backend

Companion to `implementation-plan.md`. This is the authoritative contract the frontend must implement against. It is kept in lockstep with `heatmaps-frontend/docs/api-integration.md` — the two describe the same wire format from each side; if you change one, change the other.

All error responses use the shape:

```json
{ "error": { "code": "string", "message": "human-readable string" } }
```

## `POST /api/upload`

Multipart form upload that creates a new analysis job.

**Request** (`multipart/form-data`):

| Field | Type | Notes |
|---|---|---|
| `file` | file | Video file. Validated by content-type **and** magic bytes, not just extension. Rejected if it exceeds `MAX_UPLOAD_MB` (config). |
| `heatmap_types` | string, repeated (or comma-separated) | Subset of `directional`, `speed`, `cluster`. Must contain at least one value. `roi`/`tripwire` are not accepted in v1 (see `implementation-plan.md` — no geometry input exists yet). **Not yet sent by the frontend** — see `heatmaps-frontend/docs/api-integration.md` "current implementation gaps". |

**Response `202 Accepted`:**

```json
{ "job_id": "3fa1c2e0-...-uuid" }
```

**Error responses:**

- `400` — missing `file` or `heatmap_types`.
- `415` — file is not a supported video type (checked via magic bytes).
- `413` — file exceeds `MAX_UPLOAD_MB`.
- `422` — `heatmap_types` contains an unknown/unsupported value (e.g. `roi`), or is empty.

No job is created on any error response.

## `GET /api/status/{job_id}`

Point-in-time snapshot of job state — used by the frontend to recover state after a page reload or a dropped SSE connection (not yet called anywhere in the frontend — see gaps list linked above). Same payload shape as SSE events (below), without the `event:` framing.

**Response `200`:**

```json
{ "status": "processing", "progress": 45 }
```

or, if completed:

```json
{
  "status": "completed",
  "progress": 100,
  "outputs": [
    { "type": "directional", "label": "Directional flow", "manifest_url": "https://.../media/{job_id}/directional/stream.m3u8" },
    { "type": "speed", "label": "Speed", "manifest_url": "https://.../media/{job_id}/speed/stream.m3u8" }
  ]
}
```

`outputs` is an **array**, one entry per selected heatmap type, in the order they were requested. `type` is always one of `directional`/`speed`/`cluster` — the frontend maps it to a display `label` itself (or uses the server-provided `label` directly); either way `type` is the stable key, `label` is just a suggested human string.

**Error responses:**

- `404` — unknown `job_id` (not found in Redis — may also mean it expired; see `implementation-plan.md` job-history limitation).

## `GET /api/status/{job_id}/stream`

Server-Sent Events stream of job progress. Content-Type: `text/event-stream`. The server polls job state internally (~1s interval) and emits an event on every status/progress change; the stream closes after a terminal event (`completed` or `failed`).

Event payloads (`data:` lines, JSON):

```
data: {"status": "queued"}

data: {"status": "processing", "progress": 45}

data: {"status": "completed", "progress": 100, "outputs": [
  {"type": "directional", "label": "Directional flow", "manifest_url": "https://.../directional/stream.m3u8"},
  {"type": "speed", "label": "Speed", "manifest_url": "https://.../speed/stream.m3u8"}
]}
```

or on failure:

```
data: {"status": "failed", "error": "unsupported codec in source video"}
```

`manifest_url` values are absolute URLs on the backend's own host (local-disk storage served via `StaticFiles` in v1) — not assumed to be a CDN/S3 URL. CORS on the backend must allow the frontend origin for both `/api/*` and `/media/*` so `hls.js` can fetch manifests/segments cross-origin in dev (Vite proxies `/api`, but media may be fetched directly against `VITE_API_URL`).

## `GET /health`

Liveness/readiness probe. Checks actual Redis connectivity (not a hardcoded response).

- `200` — Redis reachable: `{"status": "ok", "workers_online": <int>, "queued_jobs": <int>}`. `workers_online` is the number of RQ workers currently registered on the `video-processing` queue; `queued_jobs` is jobs waiting to be picked up (not counting ones already `processing`). `workers_online == 0 && queued_jobs > 0` means uploads are accepted but nothing will ever process them — the direct diagnosis for "upload succeeded but progress is stuck at 0%".
- `503` — Redis unreachable or other dependency failure; body includes `{"error": {...}}` with the failing dependency named.

## Static media

Completed HLS output is served as static files:

```
GET /media/{job_id}/{heatmap_type}/stream.m3u8
GET /media/{job_id}/{heatmap_type}/segment_XXX.ts
```

`{job_id}` and `{heatmap_type}` are validated against the known job/type set before serving (no arbitrary path traversal via these segments).
