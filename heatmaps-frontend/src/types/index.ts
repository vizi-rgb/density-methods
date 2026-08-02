export type AppState =
  | 'IDLE'
  | 'UPLOADING'
  | 'PROCESSING'
  | 'READY_TO_PLAY'
  | 'ERROR';

export interface VideoOutput {
  label: string;
  manifest_url: string;
}

export interface SSEEvent {
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  outputs?: VideoOutput[];
  error?: string;
}
