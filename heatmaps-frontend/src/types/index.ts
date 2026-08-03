export type AppState =
  | 'IDLE'
  | 'UPLOADING'
  | 'PROCESSING'
  | 'READY_TO_PLAY'
  | 'ERROR';

export type HeatmapType = 'directional' | 'speed' | 'cluster';

export const HEATMAP_TYPES: { value: HeatmapType; label: string }[] = [
  { value: 'directional', label: 'Directional flow' },
  { value: 'speed', label: 'Speed' },
  { value: 'cluster', label: 'Cluster' },
];

export interface VideoOutput {
  type: HeatmapType;
  label: string;
  manifest_url: string;
}

export interface SSEEvent {
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress?: number;
  outputs?: VideoOutput[];
  error?: string;
}
