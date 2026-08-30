# Acceptance Criteria — heatmaps-frontend

Companion to `frontend-plan.md` / `api-integration.md`. Checklist for the incremental-per-heatmap / MP4 redesign.

## Functional

- [x] Upload accepts a file, no other input required.
- [x] On upload success, a preview of the raw video appears immediately (`<video src={video_url}>`, no processing wait).
- [x] The "add analysis" menu is available immediately after upload and stays available — not consumed after one use.
- [x] Directional: exactly one of the 6 directions selectable; Speed: min/max both optional, independently; Cluster: integer group size ≥ 2, submit disabled below 2.
- [x] Each "Add" creates one new independent job and one new tile — existing tiles are unaffected.
- [x] Each tile shows its own progress (`queued`/`processing` with %) and, on completion, its own player — independent of every other tile's state.
- [x] A failed analysis shows an inline error in its own tile; other tiles keep working.
- [x] Grid shows an empty-state message when there are no tiles yet, and lays out multiple tiles in a responsive grid (not tabs).
- [ ] Reload mid-processing restores the video preview and every tile, each resuming its own progress — implemented (sessionStorage + per-tile self-sync) but **not visually verified** (no browser available in the build environment).
- [x] Upload failure shows an error with a reset option (`ERROR` state, global — this is the one thing still global, since without a video there's nothing else to show).
- [x] The add-analysis menu has an optional "Nazwa" field; when filled, its trimmed value becomes the tile's label instead of the auto-generated `describeHeatmapRequest` one; blank/whitespace-only falls back to the default naming — `tsc -b`/`eslint` clean, not yet visually clicked through.
- [x] A layout toggle switches all tiles between a responsive grid and a single-column stacked list without losing any tile's state.
- [x] An edit-mode toggle changes tile-click behavior: in edit mode, clicking a tile removes it from the session (client-side only — the underlying job/output on the backend is untouched); normal mode is unaffected.
- [x] Queued tiles no longer hold an open SSE connection — they poll `getHeatmapStatus` every 2s and only open an `EventSource` once a job reaches `processing`. Fixes a real bug: adding more analyses than the browser's per-origin connection pool had room for meant the 4th+ tile's own creation request stalled until an earlier tile's SSE connection closed (root-caused via investigation of both the backend, which was confirmed non-blocking, and the frontend's connection usage).
- [x] The add-analysis menu has an optional "Ustawienia wizualizacji" section (`fixed_max`/`alpha`/`sigma`), available for all three categories. All-or-nothing: 0 filled → `visualizer` omitted from the request (backend default applies); 3 filled → sent as an override; 1–2 filled → Add is disabled with an inline message. `tsc -b`/`eslint` clean, not yet visually clicked through.
- [ ] After a successful upload, a `CALIBRATING` step (`PerspectiveCalibrator`) appears before the heatmap menu: pick 4 points on a captured video frame, enter matching real-world X/Y per point, submit → `READY`; or skip straight to `READY`. `tsc -b`/`pnpm build` clean. **Not yet visually verified** — a live click-through was attempted (local backend on an alternate port so as not to disturb an already-running Docker Compose stack, real video upload) but got stuck on the frame-capture step (Konva stage never left "Wczytywanie klatki wideo...") and was interrupted before root-causing it. Re-run this before treating the calibration screen as done; see `frontend-plan.md`'s `PerspectiveCalibrator.tsx` entry for how frame capture works.
- [ ] A "Widok kamery"/"Widok z góry (world)" top-level selector appears in `HeatmapMenu`, above both the Simple/Composed toggle and the type radio group; switching it doesn't reset any already-filled type-specific fields. Selecting World View on a video where calibration was skipped shows a warning note; submitting either mode stamps `view` onto the request. `tsc -b`/`pnpm build` clean, **not yet visually verified**.

## Non-functional

- [x] No `hls.js` anywhere — removed from `package.json`, `hlsLoader.ts` deleted. Bundle size dropped from ~707KB to ~202KB as a direct result.
- [x] `EventSource` instances are closed on tile unmount and on terminal status (completed/failed) — each `HeatmapTile` manages its own via a cleanup effect. Not opened at all until the job is `processing` — see the queued-poll fix above.
- [x] Backend URL only via `VITE_API_URL`, no hardcoded URLs.
- [x] `pnpm build` clean, `pnpm lint` clean (`tsc -b` strict mode incl. `erasableSyntaxOnly`; had to fix one `react-hooks/set-state-in-effect` lint error by switching session restore to a `useState` lazy initializer instead of a mount effect).
- [x] CORS verified live end-to-end against a real backend from the actual dev-server origin (see `api-integration.md`).
- [ ] Full visual browser click-through — not done, Chrome extension unavailable in the build environment. `tsc`/`eslint`/`pnpm build` clean plus a live HTTP-contract check stand in for it; do a real click-through before treating this as fully verified.

## Scenario (manual, do this before calling it done)

| Step | Action | Expected |
|---|---|---|
| 1 | Open the app | File picker visible, nothing else |
| 2 | Choose a video, submit | Brief "wysyłanie" state, then the calibration screen appears (captured video frame) |
| 2b | Click 4 points on the frame, fill in real-world X/Y for each, click "Zatwierdź kalibrację" | Preview + add-analysis menu appear (state → `READY`) |
| 3 | Add menu: pick Directional, "right", Add | New tile appears showing "Directional — right" with a progress bar at 0% |
| 4 | Wait | Progress increases; tile switches to a playable video on completion |
| 5 | Add menu: pick Speed, leave both bounds empty, Add | Second tile appears alongside the first, independent progress |
| 6 | Add menu: pick Cluster, group size 2, Add | Third tile appears; independent progress |
| 7 | Reload the page mid-processing on one of them | Preview + all three tiles restored, each showing correct current state |
| 8 | Add a 4th and 5th analysis while the first ones are still queued/processing | Both new tiles appear immediately with a queued progress bar — do not wait for earlier tiles to finish |
| 9 | Type a name in "Nazwa" before Add | New tile shows that name instead of the auto-generated label |
| 10 | Click the layout toggle | Tiles switch from grid to a stacked list, and back on a second click |
| 11 | Click the edit-mode toggle, then click a tile | That tile disappears from the grid/list; the others are unaffected |
| 12 | Fill only "Fixed max" in the visualizer section, leave Alpha/Sigma blank | Add is disabled, inline error shown |
| 13 | Fill all three visualizer fields, Add | New tile created (request includes `visualizer`); no client-side error |
| 14 | Click "Nowe wideo" | Back to the file picker, session cleared |
| 15 | Upload a new video, skip calibration, click "Widok z góry (world)" | Warning note appears under the selector; type fields (including ROI/tripwire pickers) work exactly as in camera view |
| 16 | With World View selected, add a Directional and an ROI heatmap (drawing the polygon on the video frame as usual) | Two new tiles appear labeled "World — Directional — ..." / "World — ROI — ...", and once complete their videos have a visibly different aspect ratio/resolution than a camera-view tile |
