import { useState } from 'react';
import { VideoPlayer } from './VideoPlayer';
import type { VideoOutput } from '../types';

interface VideoPlayerGridProps {
  outputs: VideoOutput[];
}

export function VideoPlayerGrid({ outputs }: VideoPlayerGridProps) {
  const [activeTab, setActiveTab] = useState(0);

  if (outputs.length === 0) return null;

  // Single output — render without tabs
  if (outputs.length === 1) {
    return <VideoPlayer output={outputs[0]} />;
  }

  return (
    <div style={{ width: '100%', maxWidth: '720px' }}>
      <div role="tablist" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {outputs.map((output, i) => (
          <button
            key={output.manifest_url}
            role="tab"
            aria-selected={activeTab === i}
            onClick={() => setActiveTab(i)}
            style={{
              padding: '0.4rem 1rem',
              borderRadius: '4px',
              border: '1px solid #ccc',
              cursor: 'pointer',
              background: activeTab === i ? '#4caf50' : '#fff',
              color: activeTab === i ? '#fff' : 'inherit',
              fontWeight: activeTab === i ? 'bold' : 'normal',
            }}
          >
            {output.label}
          </button>
        ))}
      </div>
      <VideoPlayer output={outputs[activeTab]} />
    </div>
  );
}
