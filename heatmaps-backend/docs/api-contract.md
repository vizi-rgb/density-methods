# API Contract — heatmaps-backend

Companion to `implementation-plan.md`. This is the authoritative contract the frontend must implement against. Kept in lockstep with `heatmaps-frontend/docs/api-integration.md` — if you change one, change the other.

**This is a breaking change from an earlier version of this contract.** Upload no longer takes `heatmap_types`; a video is uploaded once, then any number of individual heatmap analyses are requested against it, each producing its own MP4 (not HLS — see `implementation-plan.md` for why HLS was dropped).

All error responses use the shape:

```json
{ "error": { "code": "string", "message": "human-readable string" } }
```

Validation failures on a JSON request body (missing/invalid fields, caught by FastAPI/pydantic) come back as `400` with `code: "invalid_request"` — this covers all the per-type validation below (invalid `direction`, `group_size < 2`, `min_speed > max_speed`, `tripwire.p1 == p2`, `roi.polygon` with fewer than 3 points), there's no separate `422` tier.

## `POST /api/videos`

Multipart upload of the raw video. No other fields.

**Request** (`multipart/form-data`): `file` — validated by content-type **and** magic bytes (`filetype`), not just extension. Rejected if it exceeds `MAX_UPLOAD_MB`.

**Response `202 Accepted`:**

```json
{ "video_id": "3fa1c2e0-...-uuid", "video_url": "http://localhost:8000/media/videos/3fa1c2e0-.../source.mp4" }
```

`video_url` is the **raw uploaded file, unmodified** — served as-is for the frontend's preview player, not transcoded. No job is created by this endpoint.

**Error responses:** `400` missing/empty file, `415` not a recognized video (magic-byte sniff failed), `413` exceeds `MAX_UPLOAD_MB`. No video is stored on any error.

## `POST /api/videos/{video_id}/heatmaps`

Creates one heatmap-analysis job against a previously uploaded video. JSON body, discriminated by `type`:

```json
{ "type": "directional", "direction": "right" }
```
```json
{ "type": "speed", "min_speed": 3.5, "max_speed": null }
```
```json
{ "type": "cluster", "group_size": 3 }
```
```json
{ "type": "tripwire", "p1": [412, 370], "p2": [1350, 400], "inside_point": [750, 750], "bucket": "inside" }
```
```json
{ "type": "roi", "polygon": [[500, 400], [1300, 400], [1300, 750], [500, 750]], "bucket": "inside" }
```

| Type | Fields | Notes |
|---|---|---|
| `directional` | `direction`: one of `all`/`static`/`up`/`down`/`left`/`right` | Exactly one — rendering shows only movement classified in that direction. |
| `speed` | `min_speed`, `max_speed`: optional numbers (km/h) | Either or both may be omitted (no lower/upper bound). `min_speed > max_speed` (when both given) is rejected. |
| `cluster` | `group_size`: integer ≥ 2 | Renders groups of **exactly** this many people (not "N or more") — matches `lib`'s DBSCAN output, which buckets by exact cluster size. `1` is rejected (DBSCAN's `min_samples=2` means no such bucket can exist). |
| `tripwire` | `p1`, `p2`: `[x, y]` pixel points forming the tripwire line; `inside_point`: `[x, y]` marking which half-plane is "inside"; `bucket`: one of `inside`/`outside`/`inside->outside`/`outside->inside` | `p1 == p2` is rejected (degenerate line). All points are in the **source video's native pixel resolution**. Rendered overlay draws the tripwire line on top of the heatmap. |
| `roi` | `polygon`: array of ≥ 3 `[x, y]` pixel points; `bucket`: one of `inside`/`outside`/`inside->outside`/`outside->inside` | Fewer than 3 points is rejected. Points are in the **source video's native pixel resolution**. Rendered overlay draws the closed polygon on top of the heatmap. `tripwire` is implemented as a special case of `roi` (`lib`'s `TripwireHeatmap` computes a half-plane polygon from the line + inside point and delegates to `RoiHeatmap`) — both share the same 4-value `bucket` enum. |

All five types also accept an optional `half_life_time` (integer seconds > 0) — an exponential decay applied to the heatmap every frame, so activity fades out over time instead of accumulating forever across the whole video. Omit it for no decay (the original all-time-accumulated behavior).

All five types also accept an optional `visualizer` object — rendering tuning knobs, unrelated to which heatmap type/params are selected:

```json
{ "type": "directional", "direction": "right", "visualizer": { "fixed_max": 1.0, "alpha": 0.9, "sigma": 5.0 } }
```

| Field | Type | Notes |
|---|---|---|
| `fixed_max` | number ≥ 0 | Upper bound the heatmap's color scale is normalized against. |
| `alpha` | number, 0–1 | Overlay opacity blended onto the source frame. |
| `sigma` | number ≥ 0 | Gaussian blur radius applied to the density map before rendering. |

All three fields are required together — there's no way to override just one and default the others. Omit `visualizer` entirely to use the server's configured defaults (`heatmap_fixed_max`/`heatmap_alpha`/`heatmap_sigma` in `app/config.py`, currently `3.0`/`0.5`/`25.0`).

### Composed jobs (`type: "composed"`)

A sixth request shape combines two or more of the five primitive types above into one job via `HeatmapLogic` (`lib/core/heatmap/logic/logic.py`), applied per-frame before rendering:

```json
{
  "type": "composed",
  "layers": [
    { "heatmap": { "type": "speed", "min_speed": 7 } },
    { "heatmap": { "type": "directional", "direction": "up" }, "operator": "AND" },
    { "heatmap": { "type": "roi", "polygon": [[500, 400], [1300, 400], [1300, 750], [500, 750]], "bucket": "inside" }, "operator": "AND_NOT" }
  ],
  "visualizer": { "fixed_max": 1.0, "alpha": 0.9, "sigma": 5.0 }
}
```

| Field | Type | Notes |
|---|---|---|
| `layers` | array, ≥ 1 entries | Evaluated in order. Each entry: `heatmap` (any of the 5 primitive request bodies above, same validation rules as standalone), `operator` (`"AND"`/`"OR"`/`"AND_NOT"`, required on every layer **except** the first — the first layer must omit it), `invert` (bool, default `false` — flips that layer's condition, e.g. "NOT inside ROI", before it's combined into the running result). |
| `visualizer` | object, optional | Same shape as the standalone `visualizer` object, but **job-level**: the combined heatmap is blended onto the frame once, not once per layer. A `visualizer` object nested inside an individual layer's `heatmap` is accepted (for schema reuse with the standalone types) but **ignored** — only the job-level one has any effect. |

Rendered overlay draws all layers' geometric shapes (tripwire lines / ROI polygons) on top of the single combined-heatmap blend.

The job's `label` (see `GET /api/heatmaps/{job_id}` below) for a composed job is a generated natural-language readout, e.g. `"Show tracks matching (Speed ≥7 km/h) AND (Moving Up) BUT NOT (Inside ROI)"` — parenthesized per layer, joined by `AND`/`OR`/`BUT NOT` (for `AND_NOT`), with `NOT (...)` wrapping any layer with `invert: true`.

**Response `202 Accepted`:** `{ "job_id": "..." }`

**Error responses:** `404` (`video_not_found`) if `video_id` doesn't exist, `400` (`invalid_request`) for any of the per-type validation above.

## `POST /api/videos/{video_id}/calibration`

Sets the perspective-transformation calibration for a previously uploaded video — a 4-point correspondence between pixel coordinates in the video frame and real-world coordinates (meters), used to build the `CameraToWorldMapper` passed into `MomentumTracker` for that video's future heatmap jobs (replacing the fixed reference-video matrix `speed` used before).

**Request:**

```json
{
  "camera_points": [[293, 174], [40, 557], [1752, 524], [1512, 149]],
  "real_world_points": [[0, 0], [0, 6], [15, 6], [15, 0]]
}
```

Both arrays are exactly 4 `[x, y]` pairs, correspondence by index (`camera_points[i]` ↔ `real_world_points[i]`) — order otherwise doesn't matter, as long as it's consistent between the two arrays. `camera_points` are pixel coordinates in the **source video's native resolution** (not a scaled-down preview).

**Response `204 No Content`.**

**Error responses:** `404` (`video_not_found`) if `video_id` doesn't exist. `400` (`invalid_calibration_points`) if the 4 points don't form a valid quadrilateral (e.g. three or more collinear) — `cv2.getPerspectiveTransform` doesn't raise for degenerate input, so the matrix is round-tripped against the request's own points to detect this. `400` (`invalid_request`) if either array isn't exactly length 4.

Calibrating is **optional** — `POST /api/videos/{video_id}/heatmaps` falls back to `lib`'s hardcoded `CameraInfo` matrix if this endpoint was never called for that `video_id`, so uncalibrated videos still work (with the same accuracy caveat as before this endpoint existed).

## `GET /api/heatmaps/{job_id}`

Point-in-time snapshot of one job — used by the frontend to recover state after a page reload or a dropped SSE connection. Same shape as SSE events below, without the `event:` framing.

```json
{ "status": "processing", "progress": 45 }
```
```json
{
  "status": "completed",
  "progress": 100,
  "output": { "type": "directional", "label": "Directional — right", "video_url": "http://.../media/jobs/{job_id}/output.mp4" }
}
```

`output` is a **single object** — one job always produces exactly one result. `label` is a ready-to-display string built from the request (`"Directional — right"`, `"Speed ≥3.5 km/h"`, `"Speed 3.5–10 km/h"`, `"Speed (any)"`, `"Cluster size 3"`, `"Tripwire — inside"`, `"ROI — outside->inside"`). For a composed job, `output.type` is `"composed"` and `label` is the generated readout described above (e.g. `"Show tracks matching (Speed ≥7 km/h) AND (Moving Up) BUT NOT (Inside ROI)"`).

**Error responses:** `404` (`job_not_found`) — unknown or expired job.

## `GET /api/heatmaps/{job_id}/stream`

Server-Sent Events. Content-Type `text/event-stream`. Polls internally (~1s) and emits an event on every status/progress change; closes after `completed`/`failed`.

```
data: {"status": "queued"}

data: {"status": "processing", "progress": 45}

data: {"status": "completed", "progress": 100, "output": {"type": "cluster", "label": "Cluster size 3", "video_url": "http://.../media/jobs/{job_id}/output.mp4"}}
```
```
data: {"status": "failed", "error": "unsupported codec in source video"}
```

`video_url` values (both here and from `POST /api/videos`) are absolute URLs on the backend's own host — plain files served via `StaticFiles`, not signed/CDN URLs. CORS must allow the frontend origin for both `/api/*` and `/media/*`.

## `GET /health`

- `200` — Redis reachable: `{"status": "ok", "workers_online": <int>, "queued_jobs": <int>}`. `workers_online == 0 && queued_jobs > 0` is the direct diagnosis for "a job is stuck, progress never moves."
- `503` — Redis unreachable; body is `{"error": {...}}`.

## Static media

```
GET /media/videos/{video_id}/source.<ext>   # raw upload, for the preview player
GET /media/jobs/{job_id}/output.mp4          # one heatmap analysis's result
```

Both are plain MP4 (h264, `-movflags +faststart` on the encoded ones so `<video>` can seek without downloading the whole file) — no manifest, no segments. `{video_id}`/`{job_id}` are server-generated UUIDs; `StaticFiles` provides the path-traversal guard.
