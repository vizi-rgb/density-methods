import { useEffect, useRef } from 'react';
import { initHls } from '../utils/hlsLoader';
import type { VideoOutput } from '../types';

interface VideoPlayerProps {
  output: VideoOutput;
}

export function VideoPlayer({ output }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    let hls: import('hls.js').default | null = null;
    try {
      hls = initHls(video, output.manifest_url);
    } catch (err) {
      console.error('HLS init error:', err);
    }

    return () => {
      hls?.destroy();
    };
  }, [output.manifest_url]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <h3 style={{ margin: 0, fontSize: '1rem' }}>{output.label}</h3>
      <video
        ref={videoRef}
        controls
        style={{ width: '100%', maxWidth: '720px', background: '#000', borderRadius: '4px' }}
      />
    </div>
  );
}
