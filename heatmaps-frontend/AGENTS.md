# AGENTS.md — heatmaps-frontend

React app: upload a video, watch progress over SSE, play back the resulting
heatmap-overlay video(s) with `hls.js`. Talks to `heatmaps-backend`.

Full design docs — read these before making non-trivial changes:
- [`docs/frontend-plan.md`](docs/frontend-plan.md) — architecture, stack, state machine, file structure.
- [`docs/api-integration.md`](docs/api-integration.md) — the backend contract as consumed here, incl. any open gaps.
- [`docs/acceptance-criteria.md`](docs/acceptance-criteria.md) — Definition of Done checklist (done vs. not-done).

## Stack

Vite 8, React 19 + TypeScript ~6 (strict-ish: `noUnusedLocals`,
`noUnusedParameters`, `erasableSyntaxOnly`), `hls.js` 1.6 for playback (MSE)
with native-HLS Safari fallback, native `fetch`/`EventSource` (no axios, no
react-query), pnpm, CSS-in-JS-free (inline styles + `App.css`/`index.css`).
No router, no state management library, no UI framework — this is
intentionally small.

## Layout

```
src/
  api/client.ts       # uploadVideo(file, heatmapTypes), getJobStatus(jobId), UploadError
  api/sseStream.ts     # openSSEStream(jobId, onMessage, onError)
  components/
    FileUpload.tsx      # file input + heatmap-type checkboxes
    JobStatus.tsx        # progress bar
    VideoPlayer.tsx      # single <video> + hls.js
    VideoPlayerGrid.tsx  # tabs over outputs[] (no tabs if only 1 output)
  utils/hlsLoader.ts   # initHls(): hls.js if supported, else native Safari HLS
  types/index.ts       # AppState, HeatmapType, HEATMAP_TYPES, VideoOutput, SSEEvent
  App.tsx              # state machine + sessionStorage-based reload recovery
```

State machine: `IDLE → UPLOADING → PROCESSING → READY_TO_PLAY` (+ `ERROR`
from anywhere). `job_id` is persisted to `sessionStorage` on upload start so
a page reload mid-job recovers via `GET /api/status/{job_id}` instead of
dropping back to `IDLE`.

## Commands

```bash
pnpm install
pnpm dev       # http://localhost:5173, proxies /api to http://localhost:8000 (vite.config.ts)
pnpm build     # tsc -b && vite build
pnpm lint      # eslint .
```

No test runner is set up. `pnpm build`+`pnpm lint` are the only current
automated checks — treat "build clean + lint clean" as the bar for a change,
and manually exercise the upload→SSE→playback flow in a browser for
anything touching `App.tsx` or the API layer.

## Non-obvious things worth knowing before touching this code

- **`erasableSyntaxOnly` (tsconfig) forbids TS constructor parameter-property
  shorthand** (`constructor(public status: number)`) even though it's
  ordinary-looking TS — it emits runtime code beyond type erasure. Declare
  the field and assign it in the constructor body instead (see
  `UploadError` in `api/client.ts`).
- **Backend contract uses an array for `outputs`**, not a map:
  `{type, label, manifest_url}[]`, one entry per *selected* heatmap type, in
  request order. `type` is the stable key (`'directional' | 'speed' |
  'cluster'`); `label` is a display string the backend already provides —
  safe to render directly. Don't reintroduce an object-map assumption; it
  was deliberately standardized to this shape (see git history around the
  docs split) to match what's already built here rather than rework it.
- **Upload must send `heatmap_types`** (repeated form field, ≥1 of
  `directional`/`speed`/`cluster` — see `HEATMAP_TYPES` in `types/index.ts`).
  `roi`/`tripwire` are intentionally not offered — they need geometry input
  (polygon/tripwire line) with no UI for it anywhere in this app.
  `FileUpload.tsx` already enforces "select ≥1 type" before enabling submit.
- **`SSEEvent.status` includes `'queued'`** and `progress` is optional (the
  `queued` payload has no `progress` field) — don't assume `progress` is
  always a number without checking status first.
- **`heatmaps-backend` is now actually implemented** (FastAPI + Redis/RQ +
  real YOLO pipeline + ffmpeg HLS encoding — see `../heatmaps-backend/`), not
  just documented. This app has **not yet been run against a live backend
  instance** — the upload/SSE/playback flow has only been verified against
  `docs/api-integration.md`'s written contract and by code review, not by an
  actual browser session hitting `../heatmaps-backend`. That's the natural
  next verification step, and the honest thing to say if asked "does this
  work end-to-end" before it's been done.
- **Backend media URLs are absolute, same-origin-or-not depending on
  `VITE_API_URL`** — `manifest_url` values point directly at the backend
  host (local disk + `StaticFiles` in backend v1, not S3/a CDN). No proxy
  rewriting needed for them; only `/api/*` goes through the Vite dev proxy.
- **This is a monorepo.** `heatmaps-frontend/`, `heatmaps-backend/`, and
  `lib/` are sibling directories under one git repo (`density-methods/`).
  Don't assume this repo's root is the git root.
