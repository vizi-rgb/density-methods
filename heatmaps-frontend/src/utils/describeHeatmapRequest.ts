import type { HeatmapRequest } from '../types';

/** Mirrors the backend's `build_label()` (app/domain/job.py) so a tile can
 * show a descriptive label immediately, before the job even starts. */
export function describeHeatmapRequest(request: HeatmapRequest): string {
  const prefix = request.view === 'world' ? 'World — ' : '';

  if (request.type === 'directional') {
    return `${prefix}Directional — ${request.direction}`;
  }

  if (request.type === 'speed') {
    const { min_speed, max_speed } = request;
    if (min_speed != null && max_speed != null) return `${prefix}Speed ${min_speed}–${max_speed} km/h`;
    if (min_speed != null) return `${prefix}Speed ≥${min_speed} km/h`;
    if (max_speed != null) return `${prefix}Speed ≤${max_speed} km/h`;
    return `${prefix}Speed (any)`;
  }

  if (request.type === 'cluster') {
    return `${prefix}Cluster size ${request.group_size}`;
  }

  if (request.type === 'tripwire') {
    return `${prefix}Tripwire — ${request.bucket}`;
  }

  return `${prefix}ROI — ${request.bucket}`;
}
