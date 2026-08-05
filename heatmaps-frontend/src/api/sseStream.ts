import type { HeatmapJobEvent } from '../types';

export function openHeatmapStream(
  jobId: string,
  onMessage: (event: HeatmapJobEvent) => void,
  onError: (err: Event) => void,
): EventSource {
  const es = new EventSource(
    `${import.meta.env.VITE_API_URL}/api/heatmaps/${jobId}/stream`,
  );
  es.onmessage = (e) => onMessage(JSON.parse(e.data as string) as HeatmapJobEvent);
  es.onerror = onError;
  return es;
}
