# AGENTS.md — heatmaps-frontend

React app: upload a video once, then incrementally add independent,
parameterized heatmap analyses (directional/speed/cluster) against it, each
landing as its own tile in a grid as it completes. Talks to
`heatmaps-backend`.

Full design docs — read these before making non-trivial changes:
- [`docs/frontend-plan.md`](docs/frontend-plan.md) — architecture, stack, state machine, component breakdown.
- [`docs/api-integration.md`](docs/api-integration.md) — the backend contract as consumed here, incl. what's unverified.
- [`docs/acceptance-criteria.md`](docs/acceptance-criteria.md) — Definition of Done checklist.

## Stack

Vite 8, React 19 + TypeScript ~6 (strict: `noUnusedLocals`,
`noUnusedParameters`, `erasableSyntaxOnly`), native `fetch`/`EventSource` —
**no `hls.js`** (removed deliberately, see gotcha below), pnpm. No router,
no state management library, no UI framework — stays small on purpose.

## Layout

```
src/
  api/client.ts        # uploadVideo(file), createHeatmapJob(videoId, request), getHeatmapStatus(jobId), ApiRequestError
  api/sseStream.ts      # openHeatmapStream(jobId, onMessage, onError)
  components/
    FileUpload.tsx        # file input + submit only — no options
    VideoPreview.tsx       # raw upload playback
    HeatmapMenu.tsx          # category + per-category params + Add
    HeatmapTile.tsx           # owns ONE job end-to-end: fetch + SSE + render
    HeatmapGrid.tsx            # grid of tiles, empty-state placeholder
    JobStatus.tsx                # progress bar, reused inside HeatmapTile
  utils/describeHeatmapRequest.ts  # client-side label, mirrors backend's build_label()
  types/index.ts        # AppState, HeatmapRequest, VideoOutput, HeatmapJobEvent, HeatmapTileData
  App.tsx               # state machine + sessionStorage persistence (one blob: videoId/videoUrl/tiles)
```

State machine: `IDLE → UPLOADING → READY` (+`ERROR` for upload failure
only — per-tile failures are handled inside `HeatmapTile`, never global).
`sessionStorage` key `heatmaps.session` persists `{videoId, videoUrl,
tiles}` as one JSON blob; on reload each `HeatmapTile` independently
re-fetches its own state and reopens SSE if not yet terminal — `App.tsx`
itself has no per-job logic at all.

## Commands

```bash
pnpm install
pnpm dev       # http://localhost:5173, proxies /api to http://localhost:8000 (vite.config.ts)
pnpm build     # tsc -b && vite build
pnpm lint      # eslint .
```

No test runner. `pnpm build`+`pnpm lint` are the only automated checks.

## Non-obvious things worth knowing before touching this code

- **No `hls.js`, on purpose — don't reintroduce it without a real reason.**
  Every video (raw upload preview and every heatmap result) is a plain MP4
  now. HLS was dropped because its actual benefits (adaptive bitrate,
  progressive playback, CDN segment caching) were never used here — one
  fixed quality, self-hosted, and the backend never hands over a URL before
  a job is `completed` anyway. Removing it dropped the production bundle
  from ~707KB to ~202KB. If a future need for progressive playback (showing
  video *while* it's still processing) comes up, that requires backend
  changes too, not just switching `<video>` sources back to HLS.
- **One job = one heatmap type + params = one tile.** Second design of this
  app. The first let you select multiple types at upload and got an array
  of outputs back from one job, shown as tabs. That's gone — `output` in
  every API response is now singular, `HeatmapTile` owns exactly one job,
  and `HeatmapGrid` is a real grid (not tabs) because tiles are independent,
  not variants of the same job.
- **Cluster `group_size` is an exact match server-side**, not "N or more"
  — confirmed with the user. The number input just needs `>= 2` (matches
  backend's DBSCAN `min_samples=2`); don't add "at least N" framing to the
  label or UI copy.
- **Tile labels are computed client-side** (`describeHeatmapRequest.ts`),
  immediately at Add-time, from the exact request object — not from the
  server's `output.label` (which only exists once a job completes, so
  waiting for it would mean tiles show a placeholder for their entire
  processing time). The two should always agree since both mirror the same
  logic (`app/domain/job.py`'s `build_label` on the backend) — if you change
  one, change the other.
- **`useState(loadSession)` lazy initializer, not a mount `useEffect`**, for
  restoring `sessionStorage` in `App.tsx`. `eslint-plugin-react-hooks` 7.x's
  `set-state-in-effect` rule flags synchronous `setState` inside a mount
  effect as an anti-pattern (extra render) — the fix is computing both
  `session` and the derived initial `appState` via lazy `useState`
  initializers instead, not suppressing the rule.
- **`erasableSyntaxOnly` (tsconfig) forbids TS constructor parameter-property
  shorthand** (`constructor(public status: number)`) — declare the field
  and assign it in the constructor body instead (see `ApiRequestError` in
  `api/client.ts`).
- **CORS/contract verified live**, but **no actual browser click-through
  has been done** on this redesign — the Chrome extension wasn't connected
  in the environment this was built in. Verification so far: `tsc`/`eslint`/
  `pnpm build` clean, plus the exact HTTP calls this code makes were
  exercised against a real running backend from the real `pnpm dev` origin
  (confirmed `access-control-allow-origin` on upload, job creation, and
  both static-media routes). Do a real visual click-through before treating
  the UI itself as verified — the manual scenario in
  `docs/acceptance-criteria.md` is the one to run.
- **This is a monorepo.** `heatmaps-frontend/`, `heatmaps-backend/`, and
  `lib/` are sibling directories under one git repo (`density-methods/`).
  Don't assume this repo's root is the git root.
