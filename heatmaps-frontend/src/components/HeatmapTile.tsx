import { useEffect, useRef, useState } from 'react';
import { getHeatmapStatus } from '../api/client';
import { openHeatmapStream } from '../api/sseStream';
import { JobStatus } from './JobStatus';
import type { HeatmapJobEvent, VideoOutput } from '../types';
import {cn} from "@sglara/cn";

interface HeatmapTileProps {
  jobId: string;
  label: string;
  editMode: 'normal' | 'edit';
  onDelete: (jobId: string) => void;
}

type TileState =
  | { status: 'loading' }
  | { status: 'queued' | 'processing'; progress: number }
  | { status: 'completed'; output: VideoOutput }
  | { status: 'failed'; error: string };

/** Owns one job end-to-end: fetches its current state on mount, opens an
 * SSE stream if it isn't finished yet, and renders itself accordingly —
 * self-contained so the grid doesn't need to juggle N job state machines. */
export function HeatmapTile({ jobId, label, editMode, onDelete }: HeatmapTileProps) {
  const [state, setState] = useState<TileState>({ status: 'loading' });
  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    const applyEvent = (event: HeatmapJobEvent) => {
      if (cancelled) return;
      if (event.status === 'completed' && event.output) {
        setState({ status: 'completed', output: event.output });
      } else if (event.status === 'failed') {
        setState({ status: 'failed', error: event.error ?? 'Przetwarzanie nie powiodło się' });
      } else {
        setState({
          status: event.status === 'queued' ? 'queued' : 'processing',
          progress: event.progress ?? 0,
        });
      }
    };

    const connectStream = () => {
      const es = openHeatmapStream(
        jobId,
        (event) => {
          applyEvent(event);
          if (event.status === 'completed' || event.status === 'failed') {
            es.close();
            sseRef.current = null;
          }
        },
        () => {
          if (!cancelled) setState({ status: 'failed', error: 'Utracono połączenie SSE' });
        },
      );
      sseRef.current = es;
    };

    // Only hold a live SSE connection once a job is actually being processed.
    // Queued jobs are cheaply polled instead — otherwise every queued tile
    // pins an open connection to the backend origin, and enough of those
    // exhaust the browser's per-origin connection pool, stalling even the
    // fetch() that creates the next job.
    const pollUntilProcessing = () => {
      getHeatmapStatus(jobId)
        .then((snapshot) => {
          if (cancelled) return;
          applyEvent(snapshot);
          if (snapshot.status === 'completed' || snapshot.status === 'failed') return;
          if (snapshot.status === 'processing') {
            connectStream();
            return;
          }
          pollTimer = setTimeout(pollUntilProcessing, 2000);
        })
        .catch(() => {
          if (!cancelled) {
            setState({ status: 'failed', error: 'Nie udało się pobrać stanu zadania' });
          }
        });
    };

    pollUntilProcessing();

    return () => {
      cancelled = true;
      sseRef.current?.close();
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [jobId]);

  return (
    <div
      onClick={() => editMode === 'edit' && onDelete(jobId)}
      className={cn(editMode === 'edit' && "hover:border-red-500 hover:bg-red-400 cursor-pointer", "border-gray-200", "border rounded-lg p-3 flex flex-col gap-2")}
    >
      <h4 className="text-sm font-semibold">{label}</h4>

      {state.status === 'loading' && <p>Wczytywanie…</p>}

      {(state.status === 'queued' || state.status === 'processing') && (
        <JobStatus
          progress={state.progress}
          label={state.status === 'queued' ? 'W kolejce…' : 'Przetwarzanie…'}
        />
      )}

      {state.status === 'completed' && (
        <video controls src={state.output.video_url} className="w-full bg-black rounded" />
      )}

      {state.status === 'failed' && <p className="text-red-600">❌ {state.error}</p>}
    </div>
  );
}
