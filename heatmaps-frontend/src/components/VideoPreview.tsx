interface VideoPreviewProps {
  videoUrl: string;
}

/** The raw uploaded video, served and played as-is — no processing. */
export function VideoPreview({ videoUrl }: VideoPreviewProps) {
  return (
    <div className="flex flex-col gap-2 items-center">
      <video controls src={videoUrl} className="w-full max-w-[480px] bg-black rounded" />
    </div>
  );
}
