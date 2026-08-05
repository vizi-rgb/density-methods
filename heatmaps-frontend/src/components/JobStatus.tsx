interface JobStatusProps {
  progress: number;
  label?: string;
}

export function JobStatus({ progress, label = 'Przetwarzanie...' }: JobStatusProps) {
  return (
    <div className="w-full max-w-[500px] text-center">
      <p>{label}</p>
      <div
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        className="bg-gray-200 rounded overflow-hidden h-5"
      >
        <div
          className="bg-green-500 h-full transition-[width] duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-sm text-gray-500">{progress}%</p>
    </div>
  );
}
