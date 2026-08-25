# API Integration — heatmaps-frontend

Companion to `frontend-plan.md`. The frontend's view of the backend contract in `heatmaps-backend/docs/api-contract.md` — kept in lockstep with it; if you change one, change the other.

This is a breaking change from an earlier version of both this doc and the actual frontend code — upload no longer takes a type selection; a video is uploaded once, then any number of individually parameterized heatmap jobs are created against it. HLS is gone — every video is a plain MP4.

## `POST /api/videos`

```typescript
const form = new FormData();
form.append('file', file);
fetch(`${VITE_API_URL}/api/videos`, { method: 'POST', body: form });
// -> 202 { video_id: string, video_url: string }
```

`video_url` is the raw upload, served as-is — used directly for the preview `<video>`. No job is created by this call. Implemented in `src/api/client.ts`'s `uploadVideo`.

**Errors**: `400` empty file, `415` not a recognized video (magic-byte sniff), `413` over the size limit. Surfaced via `ApiRequestError` (has `.status` + a `.message` parsed from the response body's `{"error":{"message"}}`, or a Polish status-specific fallback).

## `POST /api/videos/{video_id}/heatmaps`

```typescript
fetch(`${VITE_API_URL}/api/videos/${videoId}/heatmaps`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(request), // HeatmapRequest — see types/index.ts
});
// -> 202 { job_id: string }
```

`request` is one of:
```typescript
{ type: 'directional', direction: 'all'|'static'|'up'|'down'|'left'|'right', half_life_time?: number, visualizer?: HeatmapVisualizerRequest }
{ type: 'speed', min_speed?: number, max_speed?: number, half_life_time?: number, visualizer?: HeatmapVisualizerRequest }
{ type: 'cluster', group_size: number, half_life_time?: number, visualizer?: HeatmapVisualizerRequest }  // integer >= 2, EXACT match server-side, not "N or more"
{ type: 'tripwire', p1: Point, p2: Point, inside_point: Point, bucket: RegionBucket, half_life_time?: number, visualizer?: HeatmapVisualizerRequest }
{ type: 'roi', polygon: Point[], bucket: RegionBucket, half_life_time?: number, visualizer?: HeatmapVisualizerRequest }  // polygon needs >= 3 points
```
```typescript
type RegionBucket = 'inside' | 'outside' | 'inside->outside' | 'outside->inside';

interface HeatmapVisualizerRequest {
  fixed_max: number; // >= 0
  alpha: number;      // 0-1
  sigma: number;       // >= 0
}
```

`half_life_time` (seconds, integer > 0) is optional on all five types — applies exponential decay to the heatmap every frame so old activity fades out instead of accumulating for the whole video. Omit for no decay.

`visualizer` is optional on all five types and, per the backend contract, all-or-nothing — there's no way to override just `alpha` and default `fixed_max`/`sigma`. `HeatmapMenu` (see `frontend-plan.md`) enforces this client-side: Add is disabled unless 0 or 3 of the three fields are filled. Omitting `visualizer` entirely makes the backend use its configured defaults (`heatmap_fixed_max`/`heatmap_alpha`/`heatmap_sigma`, see `heatmaps-backend/docs/api-contract.md`).

`tripwire`'s `p1`/`p2` are the two line endpoints and `inside_point` marks which half-plane is "inside" — all three collected via `TripwirePicker` (a Konva modal over a captured video frame, opened from `HeatmapMenu`), in the source video's native pixel resolution (same rescale-on-submit pattern as `PerspectiveCalibrator`, see below). `roi`'s `polygon` is collected the same way via `RoiPicker`, with no point cap (minimum 3 to submit) and a closed-polygon live preview. Both share the same `bucket` selector (`RegionBucket`) since `tripwire` is implemented server-side as a special case of `roi` — a half-plane polygon computed from the line + inside point.

Implemented in `src/api/client.ts`'s `createHeatmapJob`. **Errors**: `404 video_not_found` for an unknown `video_id`, `400 invalid_request` for any per-type validation failure (bad `direction`, `group_size < 2`, `min_speed > max_speed`, `tripwire.p1 == p2`, `roi.polygon` under 3 points) — there's no separate `422` tier, everything body-validation-related is `400`.

## `POST /api/videos/{video_id}/calibration`

```typescript
fetch(`${VITE_API_URL}/api/videos/${videoId}/calibration`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ camera_points: cameraPoints, real_world_points: realWorldPoints }), // Point[] = [number, number][]
});
// -> 204 No Content
```

Sets the per-video perspective calibration (4-point pixel↔real-world correspondence, index-matched between the two arrays) used server-side to build that video's `CameraToWorldMapper`. `camera_points` must be in the **source video's native pixel resolution**, not the scaled-down preview a user picks points on — `PerspectiveCalibrator` converts stage-display coordinates back to native before sending (multiplies by `naturalWidth / stageWidth`).

Implemented in `src/api/client.ts`'s `submitCalibration`. **Errors**: `404 video_not_found` for an unknown `video_id`, `400 invalid_calibration_points` if the 4 points are degenerate (e.g. collinear), `400 invalid_request` if either array isn't exactly length 4.

Calling this is optional from the backend's perspective — skipping it (the calibration screen's "Pomiń kalibrację" button) leaves the backend's hardcoded fallback matrix in place for that video's future heatmap jobs.

## `GET /api/heatmaps/{job_id}` (snapshot, for reconnect) & `GET /api/heatmaps/{job_id}/stream` (SSE)

```typescript
fetch(`${VITE_API_URL}/api/heatmaps/${jobId}`);              // getHeatmapStatus
new EventSource(`${VITE_API_URL}/api/heatmaps/${jobId}/stream`); // openHeatmapStream
```

Event/response payloads:

```
{"status": "queued"}
{"status": "processing", "progress": 45}
{"status": "completed", "progress": 100, "output": {"type": "directional", "label": "Directional — right", "video_url": "http://.../media/jobs/{job_id}/output.mp4"}}
{"status": "failed", "error": "..."}
```

`output` is a **single object**, not an array — one job always produces exactly one result now. `HeatmapTile` (see `frontend-plan.md`) owns this whole lifecycle per job: snapshot on mount, then it either polls or opens SSE depending on status, and renders accordingly. There's no reconnect logic in `App.tsx` itself — each tile is independently responsible for its own job, and `App.tsx` only needs to remember `{jobId, label}` pairs (persisted in `sessionStorage`) for tiles to re-attach to on reload.

**Client-side connection strategy (not a contract change, but load-bearing for correctness):** `HeatmapTile` does **not** open an `EventSource` for a `queued` job — it re-fetches `GET /api/heatmaps/{job_id}` every 2s instead, and only switches to the SSE stream once a snapshot comes back `processing`. Reason: the backend's `GET .../stream` connection stays open for a job's entire queued+processing lifetime (`_sse_events` only returns on `completed`/`failed`), and the backend deployment runs a single sequential `rq worker --worker-class SimpleWorker`, so several jobs can sit `queued` simultaneously for a while. If every queued tile held its own SSE connection immediately, enough of them (plus the video-preview connection, same origin) would exhaust the browser's per-origin HTTP/1.1 connection pool — and the *next* `fetch()` call, including the `POST .../heatmaps` that creates a new job, would stall in the browser's network queue until a connection freed up. Practically: adding a 4th+ analysis while 3 others were still in flight meant the new tile never appeared until an earlier one finished. Polling while `queued` keeps connections short-lived; at most one job is ever `processing` at a time given the single-worker backend, so at most one tile ever holds a long-lived SSE connection.

`video_url` (from both this and `POST /api/videos`) is an absolute URL on the backend's own host — passed straight to a `<video>` tag, nothing HLS-specific needed. Backend CORS must allow the frontend origin for both `/api/*` and `/media/*` — verified live against a running backend + `pnpm dev` (real `Origin: http://localhost:5173` header, `access-control-allow-origin` present on all three: upload, job creation, and both static-media routes).

## `GET /health`

Not used by the frontend.

## Current implementation status

- [x] Upload has no type selection (moved to per-analysis `HeatmapMenu`).
- [x] `HeatmapRequest` discriminated union matches the backend's schema exactly, including `group_size`'s exact-match semantics.
- [x] Singular `output` (not array) consumed correctly.
- [x] Optional `visualizer` field sent when the menu's three fields are all filled, omitted otherwise — client-side all-or-nothing validation matches the backend's requirement.
- [x] Optional `half_life_time` sent when set, omitted otherwise, on all five types.
- [x] `tripwire`/`roi` geometry (`TripwirePicker`/`RoiPicker`, both Konva modals over a captured video frame) collected in native pixel resolution and submitted alongside a shared `RegionBucket` selector.
- [x] Reload recovery — verified via `sessionStorage` persistence design; each tile re-syncs independently.
- [x] CORS verified live against a real running backend from the actual `pnpm dev` origin (upload, job creation, video preview, job output).
- [ ] Full visual browser click-through (upload → add all 5 types, including placing tripwire/roi points → tiles render and play) — **not done**. The Chrome extension wasn't connected in the environment this was built in; verification instead covered `tsc`/`eslint`/`pnpm build` (all clean) plus the exact HTTP contract exercised live with matching CORS headers, and the backend side against real YOLO inference. Do a real click-through before considering this fully done.
