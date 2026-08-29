export type AppState = 'IDLE' | 'UPLOADING' | 'CALIBRATING' | 'READY' | 'ERROR';

export type Point = [number, number];

export interface CalibrationRequest {
  camera_points: Point[];
  real_world_points: Point[];
}

export type Direction = 'all' | 'static' | 'up' | 'down' | 'left' | 'right';

export const DIRECTIONS: Direction[] = ['all', 'static', 'up', 'down', 'left', 'right'];

export interface HeatmapVisualizerRequest {
  fixed_max: number;
  alpha: number;
  sigma: number;
}

export type RegionBucket = 'inside' | 'outside' | 'inside->outside' | 'outside->inside';

export const REGION_BUCKETS: RegionBucket[] = ['inside', 'outside', 'inside->outside', 'outside->inside'];

export type HeatmapRequest =
  | { type: 'directional'; direction: Direction; half_life_time?: number; visualizer?: HeatmapVisualizerRequest }
  | { type: 'speed'; min_speed?: number; max_speed?: number; half_life_time?: number; visualizer?: HeatmapVisualizerRequest }
  | { type: 'cluster'; group_size: number; half_life_time?: number; visualizer?: HeatmapVisualizerRequest }
  | {
      type: 'tripwire';
      p1: Point;
      p2: Point;
      inside_point: Point;
      bucket: RegionBucket;
      half_life_time?: number;
      visualizer?: HeatmapVisualizerRequest;
    }
  | {
      type: 'roi';
      polygon: Point[];
      bucket: RegionBucket;
      half_life_time?: number;
      visualizer?: HeatmapVisualizerRequest;
    };

export type Operator = 'AND' | 'OR' | 'AND_NOT';

export interface HeatmapLayer {
  heatmap: HeatmapRequest;
  operator?: Operator;
  invert?: boolean;
}

export interface ComposedHeatmapRequest {
  type: 'composed';
  layers: HeatmapLayer[];
  visualizer?: HeatmapVisualizerRequest;
}

export type HeatmapJobRequest = HeatmapRequest | ComposedHeatmapRequest;

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
