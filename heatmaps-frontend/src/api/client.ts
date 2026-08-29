import type {
  CalibrationRequest,
  HeatmapJobEvent,
  HeatmapJobRequest,
  VisualizerDefaultsResponse,
} from '../types';

export class ApiRequestError extends Error {
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
      return 'Nieprawidłowe dane żądania.';
    case 404:
      return 'Nie znaleziono wideo lub zadania.';
    case 413:
      return 'Plik jest za duży.';
    case 415:
      return 'Nieobsługiwany format pliku.';
    default:
      return `Błąd serwera (${res.status}).`;
  }
}

export async function uploadVideo(file: File): Promise<{ video_id: string; video_url: string }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/videos`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new ApiRequestError(res.status, await errorMessageFor(res));
  return res.json() as Promise<{ video_id: string; video_url: string }>;
}

export async function createHeatmapJob(
  videoId: string,
  request: HeatmapJobRequest,
): Promise<{ job_id: string }> {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/videos/${videoId}/heatmaps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new ApiRequestError(res.status, await errorMessageFor(res));
  return res.json() as Promise<{ job_id: string }>;
}

export async function getHeatmapStatus(jobId: string): Promise<HeatmapJobEvent> {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/heatmaps/${jobId}`);
  if (!res.ok) throw new ApiRequestError(res.status, await errorMessageFor(res));
  return res.json() as Promise<HeatmapJobEvent>;
}

export async function submitCalibration(
  videoId: string,
  request: CalibrationRequest,
): Promise<void> {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/videos/${videoId}/calibration`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new ApiRequestError(res.status, await errorMessageFor(res));
}

export async function getVisualizerDefaults(): Promise<VisualizerDefaultsResponse> {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/defaults`);
  if (!res.ok) throw new ApiRequestError(res.status, await errorMessageFor(res));
  return res.json() as Promise<VisualizerDefaultsResponse>;
}
