import type { HeatmapRequest } from '../types';

/** Mirrors the backend's `build_label()` (app/domain/job.py) so a tile can
 * show a descriptive label immediately, before the job even starts. */
export function describeHeatmapRequest(request: HeatmapRequest): string {
  if (request.type === 'directional') {
    return `Directional — ${request.direction}`;
  }

  if (request.type === 'speed') {
    const { min_speed, max_speed } = request;
    if (min_speed != null && max_speed != null) return `Speed ${min_speed}–${max_speed} km/h`;
    if (min_speed != null) return `Speed ≥${min_speed} km/h`;
    if (max_speed != null) return `Speed ≤${max_speed} km/h`;
    return 'Speed (any)';
  }

  if (request.type === 'cluster') {
    return `Cluster size ${request.group_size}`;
  }

  if (request.type === 'tripwire') {
    return `Tripwire — ${request.bucket}`;
  }

  return `ROI — ${request.bucket}`;
}
