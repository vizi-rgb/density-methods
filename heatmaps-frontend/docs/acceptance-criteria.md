# Acceptance Criteria — heatmaps-frontend

Companion to `frontend-plan.md` / `api-integration.md`. Checklist for the current flow plus the gaps documented in `api-integration.md`.

## Functional

- [x] Użytkownik może wybrać plik wideo i kliknąć "Upload".
- [ ] Użytkownik może wybrać co najmniej jeden typ heatmapy (`directional`/`speed`/`cluster`) przed wysłaniem — **nie zaimplementowane**, patrz `api-integration.md`.
- [x] Po wysłaniu aplikacja przechodzi do stanu `PROCESSING` z widocznym paskiem postępu.
- [x] Pasek postępu aktualizuje się w czasie rzeczywistym przez SSE (0% → 100%).
- [x] Po otrzymaniu `status == "completed"` SSE zostaje zamknięty (`EventSource.close()`).
- [x] Wszystkie wideo z `outputs[]` są renderowane — każde w osobnym odtwarzaczu z labelem.
- [x] Gdy `outputs` ma 1 element — wyświetlany jest pojedynczy odtwarzacz (brak niepotrzebnych tabs).
- [x] Przeglądarki z natywnym HLS (Safari) działają bez hls.js.
- [x] Każdy błąd (upload, SSE, HLS) wyświetla komunikat + opcję reset do `IDLE`.
- [ ] Błędy uploadu (`400`/`413`/`415`/`422`) wyświetlają konkretny komunikat zamiast ogólnego — **nie zaimplementowane**.
- [ ] Odświeżenie strony w trakcie `PROCESSING`/`READY_TO_PLAY` odzyskuje stan przez `GET /api/status/{job_id}` zamiast wracać do `IDLE` — **nie zaimplementowane**, patrz `api-integration.md`.

## Niefunkcjonalne

- [x] Brak wycieków pamięci — `EventSource` i wszystkie instancje `Hls` (jedna per output) są niszczone przy unmount/reset.
- [x] URL backendu tylko przez `VITE_API_URL` (brak hardcoded URL).
- [ ] `pnpm build` kończy się bez błędów — zweryfikować po dodaniu selekcji typów.
- [ ] `tsc` bez błędów typów (TypeScript strict) — zweryfikować po dodaniu pola `type` do `VideoOutput`.

## Scenariusz E2E (test manualny, docelowy — po uzupełnieniu gaps)

| Krok | Akcja | Oczekiwany wynik |
|---|---|---|
| 1 | Otwarcie aplikacji | Formularz wyboru pliku + selekcji typów heatmapy widoczny |
| 2 | Wybór pliku, zaznaczenie ≥1 typu, klik Upload | Spinner / info o wysyłaniu |
| 3 | Backend zwraca `job_id` | Pasek postępu pojawia się |
| 4 | SSE: `{"status":"processing","progress":50}` | Pasek pokazuje 50% |
| 5 | SSE: `{"status":"completed","progress":100,"outputs":[...]}` | Grid/tabs N odtwarzaczy pojawia się (N = liczba wybranych typów) |
| 6 | Każde wideo ładuje się i odtwarza | Płynne odtwarzanie HLS dla każdego outputu |
| 7 | Odświeżenie strony w trakcie kroku 4 lub 6 | Stan odzyskany przez `GET /api/status/{job_id}`, bez powrotu do `IDLE` |
| 8 | Klik "Reset" | Powrót do stanu `IDLE` |

## Scenariusz E2E (obecny stan, bez gaps)

| Krok | Akcja | Oczekiwany wynik |
|---|---|---|
| 1 | Otwarcie aplikacji | Formularz wyboru pliku widoczny |
| 2 | Wybór pliku + klik Upload | Spinner / info o wysyłaniu |
| 3 | Backend zwraca `job_id` | Pasek postępu pojawia się |
| 4 | SSE: `{"status":"processing","progress":50}` | Pasek pokazuje 50% |
| 5 | SSE: `{"status":"completed","progress":100,"outputs":[...]}` | Grid/tabs N odtwarzaczy pojawia się |
| 6 | Każde wideo ładuje się i odtwarza | Płynne odtwarzanie HLS dla każdego outputu |
| 7 | Klik "Reset" | Powrót do stanu `IDLE` |
