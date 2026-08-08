export type AppState = 'IDLE' | 'UPLOADING' | 'READY' | 'ERROR';

export type Direction = 'all' | 'static' | 'up' | 'down' | 'left' | 'right';

export const DIRECTIONS: Direction[] = ['all', 'static', 'up', 'down', 'left', 'right'];

export interface HeatmapVisualizerRequest {
  fixed_max: number;
  alpha: number;
  sigma: number;
}

export type HeatmapRequest =
  | { type: 'directional'; direction: Direction; visualizer?: HeatmapVisualizerRequest }
  | { type: 'speed'; min_speed?: number; max_speed?: number; visualizer?: HeatmapVisualizerRequest }
  | { type: 'cluster'; group_size: number; visualizer?: HeatmapVisualizerRequest };

export interface VideoOutput {
  type: string;
  label: string;
  video_url: string;
}

export interface HeatmapJobEvent {
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress?: number;
  output?: VideoOutput;
  error?: string;
}

export interface VisualizerDefaultsResponse {
  fixed_max: number,
  alpha: number,
  sigma: number
}

/** One entry in the results grid — a job that's been requested, tracked
 * client-side from the moment "Add" is clicked. */
export interface HeatmapTileData {
  jobId: string;
  label: string;
}
