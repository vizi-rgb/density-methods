import type { VideoOutput } from '../types';

export async function uploadVideo(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ job_id: string }>;
}

export type { VideoOutput };
