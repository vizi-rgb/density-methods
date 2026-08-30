import type { HeatmapLayer, HeatmapRequest, Operator, View } from '../types';

/** Mirrors the backend's `build_composed_label`/`_layer_condition_phrase`
 * (app/domain/job.py) so the composer can show a live readout, and a tile
 * can show a descriptive label immediately, before the job even starts. */

const DIRECTION_PHRASES: Record<string, string> = {
  up: 'Moving Up',
  down: 'Moving Down',
  left: 'Moving Left',
  right: 'Moving Right',
  static: 'Stationary',
  all: 'Any Direction',
};

const REGION_BUCKET_PHRASES: Record<string, string> = {
  inside: 'Inside',
  outside: 'Outside',
  'inside->outside': 'Exiting',
  'outside->inside': 'Entering',
};

const OPERATOR_WORDS: Record<Operator, string> = {
  AND: 'AND',
  OR: 'OR',
  AND_NOT: 'BUT NOT',
};

function speedPhrase(request: Extract<HeatmapRequest, { type: 'speed' }>): string {
  const { min_speed, max_speed } = request;
  if (min_speed != null && max_speed != null) return `Speed ${min_speed}–${max_speed} km/h`;
  if (min_speed != null) return `Speed ≥${min_speed} km/h`;
  if (max_speed != null) return `Speed ≤${max_speed} km/h`;
  return 'Speed (any)';
}

export function describeLayerCondition(request: HeatmapRequest): string {
  if (request.type === 'directional') {
    return DIRECTION_PHRASES[request.direction];
  }

  if (request.type === 'speed') {
    return speedPhrase(request);
  }

  if (request.type === 'cluster') {
    return `Cluster Size ${request.group_size}`;
  }

  if (request.type === 'tripwire') {
    return `${REGION_BUCKET_PHRASES[request.bucket]} Tripwire`;
  }

  return `${REGION_BUCKET_PHRASES[request.bucket]} ROI`;
}

/** `view` is job-level (ComposedHeatmapRequest.view), not per-layer — a
 * layer's own nested `heatmap.view` is never read, same as the backend. */
export function describeComposedLayers(layers: HeatmapLayer[], view?: View): string {
  const parts = layers.map((layer, i) => {
    let phrase = describeLayerCondition(layer.heatmap);
    if (layer.invert) phrase = `NOT ${phrase}`;
    phrase = `(${phrase})`;
    if (i === 0) return phrase;
    return `${OPERATOR_WORDS[layer.operator ?? 'AND']} ${phrase}`;
  });
  const prefix = view === 'world' ? 'World — ' : '';
  return `${prefix}Show tracks matching ${parts.join(' ')}`;
}
