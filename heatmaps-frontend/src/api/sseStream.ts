import type { SSEEvent } from '../types';

export function openSSEStream(
  jobId: string,
  onMessage: (event: SSEEvent) => void,
  onError: (err: Event) => void,
): EventSource {
  const es = new EventSource(
    `${import.meta.env.VITE_API_URL}/api/status/${jobId}/stream`,
  );
  es.onmessage = (e) => onMessage(JSON.parse(e.data as string) as SSEEvent);
  es.onerror = onError;
  return es;
}
