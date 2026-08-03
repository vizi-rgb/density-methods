# API Integration — heatmaps-frontend

Companion to `frontend-plan.md`. This is the frontend's view of the backend contract defined in `heatmaps-backend/docs/api-contract.md` — kept in lockstep with it; if you change one, change the other.

Backend has no running code yet (docs only), so none of this has been integration-tested against a live server — the frontend implementation below matches the documented contract but has only been verified via `tsc -b`/`eslint`/`vite build` and code review.

## `POST /api/upload`

**Implemented** (`src/api/client.ts`, `src/components/FileUpload.tsx`):

```typescript
const form = new FormData();
form.append('file', file);
heatmapTypes.forEach((type) => form.append('heatmap_types', type));
fetch(`${VITE_API_URL}/api/upload`, { method: 'POST', body: form });
// -> { job_id: string }
```

`FileUpload.tsx` renders a checkbox per entry in `HEATMAP_TYPES` (`directional`/`speed`/`cluster`, from `src/types/index.ts`) and disables submit until ≥1 is checked and a file is chosen, matching the backend's "at least one, subset of {directional, speed, cluster}" requirement. `roi`/`tripwire` are intentionally not offered — no geometry-input UI exists.

**Error handling**: `uploadVideo` throws `UploadError` (has `.status` + a `.message` derived from the response body's `{"error":{"message"}}` if present, else a status-specific Polish fallback for `400`/`413`/`415`/`422`/other). `App.tsx` renders `err.message` directly in the `ERROR` state.

**Response `202`:** `{ "job_id": "string" }` — handled; persisted to `sessionStorage` (`heatmaps.jobId`) immediately after a successful upload, for reload recovery (see below).

## `GET /api/status/{job_id}` (snapshot, for reconnect)

**Implemented** (`src/api/client.ts` `getJobStatus`, `src/App.tsx` mount effect).

On mount, `App.tsx` checks `sessionStorage` for a persisted `job_id`. If present, it calls `getJobStatus(jobId)`:
- `completed` → restores `outputs`, jumps straight to `READY_TO_PLAY`.
- `failed` → clears the stored id, shows the error.
- otherwise (`queued`/`processing`) → restores `progress`, sets `PROCESSING`, and reopens the SSE stream via `connectStream(jobId)` to keep receiving live updates.
- A failed lookup (e.g. `404` — job expired/unknown) clears the stored id and silently falls back to `IDLE`.

The stored `job_id` is cleared on `reset()` and on a terminal `failed` event/snapshot; it is intentionally kept through `completed` so a reload while `READY_TO_PLAY` still restores playback.

## `GET /api/status/{job_id}/stream` (SSE)

**Implemented** (`src/api/sseStream.ts`, `App.tsx` `connectStream`):

```typescript
new EventSource(`${VITE_API_URL}/api/status/${jobId}/stream`)
```

Event payloads handled:

```
data: {"status": "queued"}

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

`SSEEvent.status` includes `'queued'` and `progress` is optional (`queued` payload has no `progress` field) — `types/index.ts` reflects this. `outputs` is an array, one entry per **selected** heatmap type. `VideoOutput` now carries `type: HeatmapType` alongside `label`/`manifest_url`.

`manifest_url` is an absolute URL on the backend's own host (local-disk storage served via `StaticFiles` in v1) — passed straight to `hlsLoader`/`hls.js`. Backend CORS must allow the frontend origin for both `/api/*` and `/media/*`.

## `GET /health`

Not used by the frontend — no action needed for the core flow.

## Implementation status

- [x] `heatmap_types` selection UI + wiring through `FileUpload.tsx` → `client.ts` → upload request.
- [x] Distinguish upload error codes (`400`/`413`/`415`/`422`) with specific user-facing messages.
- [x] `VideoOutput.type` field added to `types/index.ts`.
- [x] Reconnect/reload recovery via `GET /api/status/{job_id}` + persisted `job_id`.
- [ ] Live E2E verification against a real backend — not possible yet, `heatmaps-backend` has no running endpoints (docs only). Re-verify once the backend is implemented.
