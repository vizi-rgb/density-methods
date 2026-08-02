# API Integration — heatmaps-frontend

Companion to `frontend-plan.md`. This is the frontend's view of the backend contract defined in `heatmaps-backend/docs/api-contract.md` — kept in lockstep with it; if you change one, change the other.

Backend has no running code yet (docs only). This doc describes the contract the frontend already codes against for the parts that are stable, and flags precisely what's still missing.

## `POST /api/upload`

**Currently implemented** (`src/api/client.ts`):

```typescript
const form = new FormData();
form.append('file', file);
fetch(`${VITE_API_URL}/api/upload`, { method: 'POST', body: form });
// -> { job_id: string }
```

**Gap:** the backend requires an additional `heatmap_types` field — at least one of `directional`, `speed`, `cluster` (`roi`/`tripwire` are out of scope in v1, they need geometry input no UI collects). Today's upload sends `file` only, so every upload will be rejected by the real backend with `422` once it exists. To implement:

- Add a multi-select control to `FileUpload.tsx` (checkboxes for the 3 types, at least one required).
- `uploadVideo(file, heatmapTypes: string[])` in `client.ts` should append one `form.append('heatmap_types', t)` per selected type (repeated form field — matches backend's `string, repeated` spec).
- `onUpload` callback signature in `App.tsx`/`FileUpload.tsx` needs to carry the selected types through to `uploadVideo`.

**Response `202`:** `{ "job_id": "string" }` — unchanged, already correctly handled.

**Error responses to handle** (not distinguished today — `client.ts` only checks `res.ok`):

- `400` — missing `file`/`heatmap_types`
- `415` — unsupported file type
- `413` — file too large
- `422` — invalid/empty `heatmap_types`

## `GET /api/status/{job_id}` (snapshot, for reconnect)

**Not implemented yet.** `App.tsx` currently holds all job state in React memory only — a page reload during `PROCESSING` or `READY_TO_PLAY` loses everything and returns to `IDLE`.

**Gap, to implement:**

- Persist `job_id` (e.g. `sessionStorage`) when a job starts.
- On mount, if a persisted `job_id` exists, call `GET /api/status/{job_id}` to fetch a snapshot and restore `appState`/`progress`/`outputs` before deciding whether to also (re)open the SSE stream.
- Response shape is identical to a non-terminal/terminal SSE event (see below), without the `event:` framing — the existing `SSEEvent` type can be reused for it.

## `GET /api/status/{job_id}/stream` (SSE)

**Currently implemented** (`src/api/sseStream.ts`):

```typescript
new EventSource(`${VITE_API_URL}/api/status/${jobId}/stream`)
```

Event payloads:

```
data: {"status": "processing", "progress": 45}

data: {
  "status": "completed",
  "progress": 100,
  "outputs": [
    { "type": "directional", "label": "Directional flow", "manifest_url": "http://localhost:8000/media/{job_id}/directional/stream.m3u8" },
    { "type": "speed", "label": "Speed", "manifest_url": "http://localhost:8000/media/{job_id}/speed/stream.m3u8" }
  ]
}

data: {"status": "failed", "error": "opis błędu"}
```

`outputs` is an array, one entry per **selected** heatmap type (so its length depends on what was requested at upload, not a fixed set of 3). `type` is the stable key (`directional`/`speed`/`cluster`); `label` is a suggested display string the backend provides — safe to render directly, no client-side mapping table needed.

Current `types/index.ts` shape already matches this (`VideoOutput { label, manifest_url }`) except it's missing `type`:

```typescript
export interface VideoOutput {
  type: 'directional' | 'speed' | 'cluster'; // add this field
  label: string;
  manifest_url: string;
}
```

`manifest_url` is an **absolute URL on the backend's own host** — v1 storage is local disk served via the backend's `StaticFiles` mount, not S3/a CDN. No special handling needed beyond passing it straight to `hlsLoader`/`hls.js`; backend CORS must allow the frontend origin for both `/api/*` and `/media/*`.

## `GET /health`

Not currently used by the frontend. Not required for the core upload/status/playback flow — no action needed unless a startup health check is desired later.

## Current implementation gaps (summary)

- [ ] `heatmap_types` selection UI + wiring through `FileUpload.tsx` → `client.ts` → upload request.
- [ ] Distinguish upload error codes (`400`/`413`/`415`/`422`) with specific user-facing messages instead of one generic error.
- [ ] `VideoOutput.type` field added to `types/index.ts`.
- [ ] Reconnect/reload recovery via `GET /api/status/{job_id}` + persisted `job_id`.
