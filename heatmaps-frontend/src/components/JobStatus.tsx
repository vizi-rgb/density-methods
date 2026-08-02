interface JobStatusProps {
  progress: number;
  label?: string;
}

export function JobStatus({ progress, label = 'Przetwarzanie...' }: JobStatusProps) {
  return (
    <div style={{ width: '100%', maxWidth: '500px', textAlign: 'center' }}>
      <p>{label}</p>
      <div
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        style={{
          background: '#e0e0e0',
          borderRadius: '4px',
          overflow: 'hidden',
          height: '20px',
        }}
      >
        <div
          style={{
            background: '#4caf50',
            width: `${progress}%`,
            height: '100%',
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      <p style={{ fontSize: '0.9em', color: '#666' }}>{progress}%</p>
    </div>
  );
}
