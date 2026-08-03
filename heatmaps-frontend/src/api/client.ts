import type { HeatmapType, SSEEvent, VideoOutput } from '../types';

export class UploadError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function errorMessageFor(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (body?.error?.message) return body.error.message as string;
  } catch {
    // response body wasn't JSON — fall back to a status-specific message
  }
  switch (res.status) {
    case 400:
      return 'Brak wymaganych danych (plik lub typy heatmapy).';
    case 413:
      return 'Plik jest za duży.';
    case 415:
      return 'Nieobsługiwany format pliku.';
    case 422:
      return 'Nieprawidłowy wybór typów heatmapy.';
    default:
      return `Błąd serwera (${res.status}).`;
  }
}

export async function uploadVideo(
  file: File,
  heatmapTypes: HeatmapType[],
): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append('file', file);
  heatmapTypes.forEach((type) => form.append('heatmap_types', type));
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new UploadError(res.status, await errorMessageFor(res));
  return res.json() as Promise<{ job_id: string }>;
}

export async function getJobStatus(jobId: string): Promise<SSEEvent> {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/status/${jobId}`);
  if (!res.ok) throw new UploadError(res.status, await errorMessageFor(res));
  return res.json() as Promise<SSEEvent>;
}

export type { VideoOutput };
