# Frontend Plan — heatmaps-frontend

See also: [`api-integration.md`](./api-integration.md) (backend contract) and [`acceptance-criteria.md`](./acceptance-criteria.md) (Definition of Done).

**Second-generation design.** The original plan had the user select 1+ heatmap types up front at upload time; one job rendered all of them together as HLS streams shown in tabs. The actual product need is different: upload a video once, then **incrementally add any number of independent, parameterized heatmap analyses** to it (a direction, a speed range, an exact group size), each landing as its own tile in a grid as it finishes. HLS is gone too — every video (the raw upload preview and every heatmap result) is a plain MP4, played with a plain `<video>` tag. No `hls.js`.

## Goal

1. Upload a video (no options at upload time).
2. See a small preview of the raw upload immediately.
3. Use a persistent "add analysis" menu — pick a category (directional/speed/cluster), fill in that category's parameters, hit **Add** — to add heatmap analyses one at a time. Repeatable.
4. Each analysis appears as its own tile in a grid below, showing its own progress and then its own player, independently of the others.

## Stack

Vite 8, React 19 + TypeScript ~6 (strict-ish: `noUnusedLocals`, `noUnusedParameters`, `erasableSyntaxOnly`), native `fetch`/`EventSource` (no axios, no react-query, no `hls.js`), pnpm. Styling is Tailwind v4 (`@tailwindcss/vite` plugin, no `tailwind.config.js` needed for v4) with `@sglara/cn` for conditional `className` composition — no inline `style` objects except the one genuinely dynamic value (`JobStatus`'s progress-bar width). `index.css` is just `@import "tailwindcss";`; the old template-leftover `App.css` was deleted (dead code, never referenced by a component). No router, no state management library, no UI component library.

## Structure

```text
heatmaps-frontend/
├── docs/
│   ├── frontend-plan.md
│   ├── api-integration.md
│   └── acceptance-criteria.md
├── src/
│   ├── api/
│   │   ├── client.ts             # uploadVideo, submitCalibration, createHeatmapJob, getHeatmapStatus
│   │   └── sseStream.ts          # openHeatmapStream(jobId, ...)
│   ├── components/
│   │   ├── FileUpload.tsx         # file input + submit, no options
│   │   ├── VideoPreview.tsx        # raw upload playback
│   │   ├── PerspectiveCalibrator.tsx # frame-grab + 4-point Konva picker + real-world coords form
│   │   ├── HeatmapMenu.tsx          # Simple/Composed mode toggle + optional name + Add
│   │   ├── PrimitiveHeatmapFields.tsx # category + per-category params, shared by Simple mode & HeatmapComposer
│   │   ├── VisualizerFields.tsx       # the 3-field visualizer fieldset, shared by per-job & composed job-level use
│   │   ├── HeatmapComposer.tsx         # layer-stack builder: add/remove/reorder/operator/invert/live readout
│   │   ├── HeatmapTile.tsx           # owns one job end-to-end (poll/SSE + render + edit-mode delete)
│   │   ├── HeatmapGrid.tsx            # grid or list of HeatmapTiles, empty-state placeholder
│   │   └── JobStatus.tsx              # progress bar, used inside HeatmapTile
│   ├── utils/
│   │   ├── describeHeatmapRequest.ts   # client-side default label for the 5 simple types, mirrors backend's build_label()
│   │   ├── describeComposedLayers.ts    # client-side default label for composed jobs, mirrors backend's build_composed_label()
│   │   ├── primitiveHeatmapFields.ts     # PrimitiveFieldsValue + validity/build helpers (pure, no JSX)
│   │   └── visualizerFields.ts             # VisualizerFieldsValue + validity/build helpers (pure, no JSX)
│   ├── types/index.ts             # AppState, Point, CalibrationRequest, HeatmapRequest, HeatmapLayer, ComposedHeatmapRequest, HeatmapJobRequest, VideoOutput, HeatmapJobEvent, HeatmapTileData
│   ├── App.tsx                    # state machine + sessionStorage persistence
│   ├── main.tsx, index.css
├── .env.local                     # VITE_API_URL=http://localhost:8000
└── (vite/ts/eslint config)
```

## State machine

```
[ IDLE ] --(choose file, submit)--> [ UPLOADING ] --(video_id + video_url)--> [ CALIBRATING ] --(submit or skip)--> [ READY ]
   ^                                       |                                        |
   |                                  (upload fails)                        (calibration submit fails —
   |                                       v                                  stays in CALIBRATING, shows inline error)
   +------------------------------- [ ERROR ] (upload failure only)
```

`CALIBRATING` is a mandatory pit stop after every upload — the user marks a 4-point polygon on a frame of their own video (`PerspectiveCalibrator`, Konva-based) and enters matching real-world coordinates, or clicks "Pomiń kalibrację" to skip straight to `READY` with the backend's fallback matrix. Unlike upload failure, a failed calibration submit (`App.handleCalibrationSubmit`) does **not** transition to `ERROR` — it stays on `CALIBRATING` with `calibrationError` shown inline, so the user can retry without re-uploading.

`READY` holds `{ videoId, videoUrl, tiles: {jobId, label}[] }`, persisted as one JSON blob in `sessionStorage` (key `heatmaps.session`) so a page reload restores it — each `HeatmapTile` independently re-syncs its own job state on remount (fetch snapshot, then poll or SSE — see `HeatmapTile.tsx` below). There's no global "processing" state blocking the UI and no per-tile error is global — a failed analysis shows an error inside its own tile; everything else keeps working. Note: a page reload while still `CALIBRATING` restores straight to `READY` (session restore only checks whether a session exists, not which state it was in) — recalibrating after a reload isn't currently possible; skipping/calibrating again would need a dedicated re-entry point.

"Add" (`HeatmapMenu` → `App.handleAddHeatmap`) doesn't change `appState` at all — it stays in `READY`, just appends a new tile. The menu is never consumed/hidden after use. `App.tsx` also owns two view-only toggles that apply to the whole tile collection: `layout` (`'grid' | 'list'`, passed to `HeatmapGrid`) and `editMode` (`'normal' | 'edit'`, passed down to `HeatmapGrid` → `HeatmapTile`, with `App.handleDeleteTile` as the removal callback).

## Components

- **`FileUpload.tsx`** — `<input type="file" accept="video/*">` + submit. No heatmap-type selection here anymore — that moved to `HeatmapMenu`, per-analysis, after upload.
- **`VideoPreview.tsx`** — `<video controls src={videoUrl}>` for the raw upload, unmodified by the backend.
- **`PerspectiveCalibrator.tsx`** — shown once, right after upload, in `CALIBRATING`. Grabs a single frame from the uploaded video via an off-screen `<video crossorigin="anonymous">` seeked to ~0.1s and drawn to a `<canvas>` (needs the backend's CORS headers on `/media/*`, already required — see `api-integration.md`), then renders it as a `react-konva` `Stage` background. Click adds up to 4 draggable points (numbered, connected by a closing `Line`); once 4 are placed, a form collects real-world X/Y (meters) per point, index-matched to selection order. On submit, points are rescaled from displayed stage pixels back to the video's native resolution (`naturalWidth / stageWidth`) before calling `onSubmit(cameraPoints, realWorldPoints)` — native resolution matters because that's the pixel space the backend pipeline actually processes frames in. "Pomiń kalibrację" calls `onSkip()` directly, no validation.
- **`HeatmapMenu.tsx`** — a **Simple / Composed** mode toggle above the form:
  - Simple mode is the original single-primitive flow: an optional free-text "Nazwa" input, `PrimitiveHeatmapFields` (category radios + per-category sub-form + half-life, `showVisualizer` on), and an Add button. Calls `onAdd(request: HeatmapJobRequest, customName?: string)` on submit — the trimmed name field, or `undefined` if left blank; stays mounted and usable for the next analysis.
  - Composed mode renders `HeatmapComposer` instead (see below), same `onAdd` prop passed straight through.
- **`PrimitiveHeatmapFields.tsx`** — extracted, reusable "configure one primitive" UI, used by Simple mode directly and by `HeatmapComposer`'s "add a layer" step (`showVisualizer={false}` there):
  - Directional: radio group of `all/static/up/down/left/right`, exactly one.
  - Speed: two optional number inputs (min/max, km/h) — either, both, or neither.
  - Cluster: one number input, group size (integer ≥ 2 — matches the backend's DBSCAN-based exact-match semantics).
  - Tripwire/ROI: bucket radios + `TripwirePicker`/`RoiPicker` modal.
  - Half-life time: one optional number input, always shown regardless of `showVisualizer` (decay is per-primitive, not a rendering setting).
  - `showVisualizer` (default on): renders `VisualizerFields` inline.
- **`VisualizerFields.tsx`** — three optional number inputs — `fixed_max` (≥0), `alpha` (0–1), `sigma` (≥0) — mirroring the backend's `HeatmapVisualizerRequest`. All-or-nothing: leaving all three blank omits `visualizer` from the request entirely (backend falls back to its configured defaults); filling all three sends the override; a partial fill shows an inline error and disables submit. Used once per Simple-mode job (inside `PrimitiveHeatmapFields`) or once per composed job at the top level of `HeatmapComposer` (job-level, not per-layer).
- **`HeatmapComposer.tsx`** — the Layer Stack builder for `type: 'composed'` jobs: an ordered `HeatmapLayer[]` list (operator badge/select per layer after the first, a NOT/`invert` checkbox, ▲▼ reorder buttons, remove), an "add a layer" mini-form (`PrimitiveHeatmapFields`, `showVisualizer={false}`) with its own pending operator/invert picker, a live natural-language readout (`describeComposedLayers`), one job-level `VisualizerFields`, and a submit button disabled until ≥2 layers exist. Builds `{ type: 'composed', layers, visualizer? }` and calls the same `onAdd` prop `HeatmapMenu` passes down — lands as a single tile exactly like any other job (one job still produces exactly one output, per the "second design" note above — this doesn't reintroduce per-job output arrays).
- **`HeatmapTile.tsx`** — given `{jobId, label, editMode, onDelete}`: fetches a snapshot on mount (`getHeatmapStatus`) and renders itself: loading → progress bar → `<video>` or an inline error. While a job is `queued`, it re-polls `getHeatmapStatus` on a 2s timer instead of opening an `EventSource` — an `EventSource` is only opened once the job reaches `processing`. This matters because the backend runs a single sequential worker, so several tiles can sit `queued` at once; if each held its own long-lived SSE connection immediately, the browser's per-origin HTTP/1.1 connection cap (shared with the video preview) could saturate and stall even the `fetch()` that creates the *next* job — the fix bounds concurrent open connections to roughly "1 processing job + short polling bursts" regardless of how many analyses are queued. In `editMode === 'edit'`, clicking the tile calls `onDelete(jobId)` instead of any normal interaction (hover styling flags this). Fully self-contained; `App.tsx` never touches per-job fetch/SSE state directly, only the delete callback.
- **`HeatmapGrid.tsx`** — `layout === 'grid'` renders a CSS grid (`repeat(auto-fill, minmax(360px, 1fr))`); `layout === 'list'` renders a stacked flex column. Passes `editMode`/`onDelete` through to each `HeatmapTile`; renders an empty-state message when there are no tiles yet.
- **`JobStatus.tsx`** — the progress-bar bit, reused inside `HeatmapTile`.
- **`describeHeatmapRequest.ts`** — builds a tile's *default* label client-side, immediately on Add, from the exact request object — mirrors the backend's `build_label()` (`app/domain/job.py`) so the tile shows something meaningful (`"Directional — right"`) from the start rather than a generic "Processing…" placeholder. Only used when the menu's custom name field was left blank (`App.handleAddHeatmap` does `customName ?? describeHeatmapRequest(request)`). The label the backend returns in `output.label` on completion is the auto-generated one — irrelevant when a custom name was given, since the tile already has its label and never re-reads `output.label`.
- **`describeComposedLayers.ts`** — the composed-job counterpart, mirroring the backend's `build_composed_label`/`_layer_condition_phrase` (`app/domain/job.py`): produces the same "Show tracks matching (...) AND (...) BUT NOT (...)" readout both for `HeatmapComposer`'s live preview and as the composed tile's default label (`App.handleAddHeatmap` branches on `request.type === 'composed'` between this and `describeHeatmapRequest`).

## Edit mode

A header toggle button (`App.tsx`) switches `editMode` between `'normal'` and `'edit'`. In `'edit'`, hovering a tile highlights it (red border/background) and clicking it removes that analysis from `session.tiles` via `App.handleDeleteTile` — client-side only: it does not cancel the backend job or delete its output, it just stops the frontend from tracking/displaying it. `sessionStorage` is updated immediately so the removal survives a reload.

## Commands

```bash
pnpm install
pnpm dev       # http://localhost:5173, proxies /api to http://localhost:8000 (vite.config.ts)
pnpm build     # tsc -b && vite build
pnpm lint      # eslint .
```

No test runner is set up. `pnpm build`+`pnpm lint` are the only automated checks — manually exercise upload → preview → add each of the three analysis types → tiles complete and play, for anything touching `App.tsx` or the API layer.
