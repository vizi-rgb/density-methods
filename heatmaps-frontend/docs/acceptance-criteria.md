# Acceptance Criteria — heatmaps-frontend

Companion to `frontend-plan.md` / `api-integration.md`. Checklist for the implemented flow.

## Functional

- [x] Użytkownik może wybrać plik wideo i kliknąć "Upload".
- [x] Użytkownik może wybrać co najmniej jeden typ heatmapy (`directional`/`speed`/`cluster`) przed wysłaniem — submit zablokowany, gdy nic nie wybrano.
- [x] Po wysłaniu aplikacja przechodzi do stanu `PROCESSING` z widocznym paskiem postępu.
- [x] Pasek postępu aktualizuje się w czasie rzeczywistym przez SSE (0% → 100%), włącznie z pośrednim stanem `queued`.
- [x] Po otrzymaniu `status == "completed"` SSE zostaje zamknięty (`EventSource.close()`).
- [x] Wszystkie wideo z `outputs[]` są renderowane — każde w osobnym odtwarzaczu z labelem.
- [x] Gdy `outputs` ma 1 element — wyświetlany jest pojedynczy odtwarzacz (brak niepotrzebnych tabs).
- [x] Przeglądarki z natywnym HLS (Safari) działają bez hls.js.
- [x] Każdy błąd (upload, SSE, HLS) wyświetla komunikat + opcję reset do `IDLE`.
- [x] Błędy uploadu (`400`/`413`/`415`/`422`) wyświetlają konkretny komunikat (z body odpowiedzi lub status-specific fallback) zamiast surowego tekstu odpowiedzi.
- [x] Odświeżenie strony w trakcie `PROCESSING`/`READY_TO_PLAY` odzyskuje stan przez `GET /api/status/{job_id}` (persystowane `job_id` w `sessionStorage`) zamiast wracać do `IDLE`.

## Niefunkcjonalne

- [x] Brak wycieków pamięci — `EventSource` i wszystkie instancje `Hls` (jedna per output) są niszczone przy unmount/reset.
- [x] URL backendu tylko przez `VITE_API_URL` (brak hardcoded URL).
- [x] `pnpm build` kończy się bez błędów.
- [x] `tsc -b` bez błędów typów (TypeScript strict, `erasableSyntaxOnly`).
- [x] `pnpm lint` czysty.
- [ ] Zweryfikowane end-to-end wobec działającego backendu — **niemożliwe jeszcze**, `heatmaps-backend` nie ma zaimplementowanych endpointów (tylko dokumentacja). Do ponownej weryfikacji, gdy backend zacznie działać.

## Scenariusz E2E (manualny, do wykonania przeciwko realnemu backendowi)

| Krok | Akcja | Oczekiwany wynik |
|---|---|---|
| 1 | Otwarcie aplikacji | Formularz wyboru pliku + checkboxy typów heatmapy widoczne |
| 2 | Wybór pliku, zaznaczenie ≥1 typu, klik Upload | Spinner / info o wysyłaniu |
| 3 | Backend zwraca `job_id` | Pasek postępu pojawia się, `job_id` zapisane w `sessionStorage` |
| 4 | SSE: `{"status":"queued"}` → `{"status":"processing","progress":50}` | Pasek pokazuje 50% |
| 5 | Odświeżenie strony w trakcie kroku 4 | `GET /api/status/{job_id}` odtwarza stan `PROCESSING` z aktualnym progressem, SSE ponownie połączone — bez powrotu do `IDLE` |
| 6 | SSE: `{"status":"completed","progress":100,"outputs":[...]}` | Grid/tabs N odtwarzaczy pojawia się (N = liczba wybranych typów) |
| 7 | Każde wideo ładuje się i odtwarza | Płynne odtwarzanie HLS dla każdego outputu |
| 8 | Odświeżenie strony w trakcie kroku 7 | Stan `READY_TO_PLAY` odtworzony z `GET /api/status/{job_id}`, odtwarzacze wracają |
| 9 | Klik "Reset" | Powrót do stanu `IDLE`, `job_id` usunięte z `sessionStorage` |
| 10 | Upload pliku niebędącego wideo / za dużego pliku / bez zaznaczonego typu | Komunikat błędu odpowiadający kodowi (`415`/`413`/`422`) |
