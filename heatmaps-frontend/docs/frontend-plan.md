# Techniczny Plan Architektury Frontendu (Vite + HLS.js + SSE)

See also: [`api-integration.md`](./api-integration.md) (backend contract, current gaps) and [`acceptance-criteria.md`](./acceptance-criteria.md) (Definition of Done + E2E scenario).

## Stan Aktualny (Baseline)

| Element | Stan |
|---|---|
| Framework | Vite 8 + React 19 + TypeScript ✅ |
| `hls.js` | ✅ zainstalowany (`hls.js 1.6.x` z wbudowanymi typami) |
| `src/api/`, `src/components/`, `src/utils/`, `src/types/` | ✅ zaimplementowane (upload → SSE → tabbed HLS playback, zgodnie z tym dokumentem) |
| Backend (`heatmaps-backend`) | ⚠️ tylko dokumentacja (`heatmaps-backend/docs/`), brak działającego kodu/endpointów |
| Selekcja `heatmap_types` przy uploadzie | ✅ zaimplementowane (`FileUpload.tsx`) |
| Recovery stanu po reloadzie strony | ✅ zaimplementowane (`App.tsx`, `GET /api/status/{job_id}`) |

---

## 1. Przegląd i Cel Projektu

Celem warstwy frontendu jest dostarczenie responsywnego interfejsu użytkownika służącego do:

1. **Wysyłania pliku wideo** do przetwarzania przez Backend (FastAPI)
2. **Odbierania statusu przetwarzania w czasie rzeczywistym** poprzez jednokierunkowy strumień zdarzeń **Server-Sent Events (SSE)** oparty o `EventSource`
3. **Odtwarzania N przetworzonych wideo** — jeden na każdy wybrany typ analizy heatmapy (`directional`, `speed`, `cluster`) — przy użyciu strumieniowania HLS (`hls.js`)

> **Założenie wielowyjściowe:** jeden upload może wygenerować wiele wyjściowych wideo, po jednym na wybrany typ heatmapy. Backend zwraca tablicę `outputs[]`, a frontend renderuje N odtwarzaczy (tabs lub grid). Dokładny kontrakt: [`api-integration.md`](./api-integration.md).

---

## 2. Stos Technologiczny

| Warstwa | Technologia |
|---|---|
| Build Tool | Vite 8 |
| Framework | React 19 + TypeScript |
| Odtwarzacz Wideo | `hls.js` (MSE) + natywne HLS (Safari fallback) |
| Komunikacja Real-time | Natywny `EventSource` (SSE) |
| Komunikacja HTTP | Natywny `fetch` API |
| Style | CSS Modules (istniejące pliki zachowane) |
| Manager pakietów | pnpm |

---

## 3. Struktura Projektu (aktualna)

```text
heatmaps-frontend/
├── docs/
│   ├── frontend-plan.md          # Niniejsza dokumentacja
│   ├── api-integration.md        # Kontrakt z backendem
│   └── acceptance-criteria.md    # Definition of Done + scenariusz E2E
├── public/
│   └── favicon.svg
├── src/
│   ├── api/
│   │   ├── client.ts             # uploadVideo(file) → Promise<{ job_id }>
│   │   └── sseStream.ts          # openSSEStream(jobId, callbacks) → EventSource
│   ├── components/
│   │   ├── FileUpload.tsx         # Wybór i wysyłanie pliku
│   │   ├── JobStatus.tsx          # Pasek postępu SSE (0–100%)
│   │   ├── VideoPlayer.tsx        # Pojedynczy odtwarzacz HLS (hls.js)
│   │   └── VideoPlayerGrid.tsx    # Grid/tabs N odtwarzaczy z labelem
│   ├── utils/
│   │   └── hlsLoader.ts           # initHls() z fallback do natywnego HLS
│   ├── types/
│   │   └── index.ts               # AppState, SSEEvent, VideoOutput
│   ├── App.tsx                    # Orkiestracja stanów
│   ├── main.tsx                   # Punkt wejścia
│   ├── App.css
│   └── index.css
├── .env.local                     # VITE_API_URL=http://localhost:8000
├── index.html
├── package.json
├── tsconfig.app.json
├── tsconfig.node.json
└── vite.config.ts
```

---

## 4. Maszyna Stanów Aplikacji

```
       [ STAN: IDLE ]
             │
             ▼ (Użytkownik wybiera plik i klika Upload)
       [ STAN: UPLOADING ]
             │
             ▼ (FastAPI zwraca job_id)
       [ STAN: PROCESSING ] ◄── Otwarcie strumienia SSE (EventSource)
             │                  GET /api/status/{job_id}/stream
             │                  Strumieniowanie: 5%... 20%... 85%...
             │
             ▼ (SSE event: status == "completed", outputs[])
             │  → EventSource.close()
       [ STAN: READY_TO_PLAY ]
             │
             ▼ (Inicjalizacja N instancji hls.js — po jednej na output)
       [ Odtwarzanie N wideo (tabs / grid) ]

       Każdy etap może przejść do: [ STAN: ERROR ]
```

### Przejścia stanów

| Stan | Trigger wejścia | Widoczne elementy UI |
|---|---|---|
| `IDLE` | Start aplikacji / reset | `FileUpload` |
| `UPLOADING` | Klik "Upload" | Spinner + info o wysyłaniu |
| `PROCESSING` | `job_id` zwrócony z API | `JobStatus` (SSE progress bar) |
| `READY_TO_PLAY` | SSE `status == "completed"` | `VideoPlayerGrid` (N odtwarzaczy) |
| `ERROR` | Dowolny błąd (upload/SSE/HLS) | Komunikat błędu + przycisk reset |

> Po odświeżeniu strony w trakcie `PROCESSING`/`READY_TO_PLAY`, aplikacja odtwarza stan przez `GET /api/status/{job_id}` (persystowane `job_id` w `sessionStorage`) zamiast wracać do `IDLE`.

---

## 5. Plan Implementacji (etapy 1-6, zaimplementowane)

### Etap 1 — Zależności i konfiguracja ✅

```bash
pnpm add hls.js
pnpm add -D @types/hls.js
```

- `.env.local`: `VITE_API_URL=http://localhost:8000`
- `vite.config.ts` proxy: `'/api': 'http://localhost:8000'`

### Etap 2 — Typy współdzielone (`src/types/index.ts`) ✅

Patrz [`api-integration.md`](./api-integration.md) dla aktualnego kształtu `SSEEvent`/`VideoOutput` i brakującego pola `heatmap_types`.

### Etap 3 — Warstwa API (`src/api/client.ts`, `src/api/sseStream.ts`) ✅

Patrz [`api-integration.md`](./api-integration.md) dla dokładnych żądań/odpowiedzi.

### Etap 4 — Komponenty UI ✅

- **`FileUpload.tsx`** — `<input type="file" accept="video/*">` + checkbox group dla `heatmap_types` (min. 1 wybór wymagany) + button, callback `onUpload(file, heatmapTypes)`.
- **`JobStatus.tsx`** — pasek postępu z `progress: number` (0–100) + tekst statusu
- **`VideoPlayer.tsx`** — pojedynczy `<video>` z `ref` + inicjalizacja hls.js przez `hlsLoader`; przyjmuje `{ label, manifestUrl }`
- **`VideoPlayerGrid.tsx`** — renderuje `outputs.map(o => <VideoPlayer>)` w układzie tabs lub grid (pojedynczy output = bez tabs); niszczy wszystkie instancje `Hls` przy unmount

### Etap 5 — HLS Loader (`src/utils/hlsLoader.ts`) ✅

`Hls.isSupported()` → `hls.loadSource`/`attachMedia`; inaczej natywne `canPlayType('application/vnd.apple.mpegurl')` (Safari); inaczej rzuca błąd.

### Etap 6 — Orkiestracja w `App.tsx` ✅

`useState` dla `appState`, `progress`, `outputs`, `error`. Przepływ: `uploadVideo(file, heatmapTypes)` → persystencja `job_id` w `sessionStorage` → `connectStream()` (`openSSEStream()`) → na `completed`: zamknięcie SSE, zapis `outputs`, przejście do `READY_TO_PLAY`. Dodatkowy `useEffect` na mount odczytuje persystowane `job_id` i wywołuje `GET /api/status/{job_id}` (`getJobStatus`), odtwarzając stan (i ponownie łącząc SSE, jeśli job nie jest jeszcze zakończony). `useEffect` niszczy `EventSource` przy unmount/reset.
