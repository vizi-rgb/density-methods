import { Fragment, useEffect, useRef, useState } from 'react';
import { Stage, Layer, Image as KonvaImage, Circle, Line, Text } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import type { Point } from '../types';

const STAGE_MAX_WIDTH = 640;
const POINT_COLOR = '#22c55e';

interface RoiPickerProps {
  videoUrl: string;
  initial?: Point[] | null;
  onSubmit: (polygon: Point[]) => void;
  onCancel: () => void;
}

/** Grabs a static frame from the uploaded video and lets the user mark a
 * polygon (min. 3 points) defining a region of interest — same Konva-on-a-
 * captured-frame pattern as TripwirePicker, rendered as a modal overlay. */
export function RoiPicker({ videoUrl, initial, onSubmit, onCancel }: RoiPickerProps) {
  const [frameImage, setFrameImage] = useState<HTMLImageElement | null>(null);
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const initialRef = useRef(initial);

  // `initial` is in natural (unscaled) image coordinates — same space the
  // points get submitted in (see handleSubmit) — but the canvas draws in
  // scaled stage coordinates, and the scale factor is only known once the
  // video frame has loaded. Seed the stage-space points once that happens.
  useEffect(() => {
    if (!initialRef.current || !naturalSize) return;
    const stageWidth = Math.min(STAGE_MAX_WIDTH, naturalSize.width);
    const scale = stageWidth / naturalSize.width;
    setPoints(initialRef.current.map(([x, y]): Point => [x * scale, y * scale]));
  }, [naturalSize]);

  useEffect(() => {
    let cancelled = false;
    const video = document.createElement('video');
    video.crossOrigin = 'anonymous';
    video.muted = true;
    video.playsInline = true;
    video.preload = 'auto';
    // Off-screen but not display:none — some browsers won't decode frames
    // for a video element that's never actually rendered.
    video.style.position = 'fixed';
    video.style.width = '1px';
    video.style.height = '1px';
    video.style.opacity = '0';
    video.style.pointerEvents = 'none';
    document.body.appendChild(video);

    const captureFrame = () => {
      if (cancelled) return;
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.drawImage(video, 0, 0);
      const img = new Image();
      img.onload = () => {
        if (cancelled) return;
        setFrameImage(img);
        setNaturalSize({ width: video.videoWidth, height: video.videoHeight });
      };
      img.src = canvas.toDataURL('image/png');
    };

    const handleLoadedData = () => {
      video.currentTime = Math.min(0.1, video.duration || 0);
    };

    video.addEventListener('loadeddata', handleLoadedData);
    video.addEventListener('seeked', captureFrame);
    video.src = videoUrl;

    return () => {
      cancelled = true;
      video.removeEventListener('loadeddata', handleLoadedData);
      video.removeEventListener('seeked', captureFrame);
      document.body.removeChild(video);
    };
  }, [videoUrl]);

  const stageWidth = naturalSize ? Math.min(STAGE_MAX_WIDTH, naturalSize.width) : STAGE_MAX_WIDTH;
  const scale = naturalSize ? stageWidth / naturalSize.width : 1;
  const stageHeight = naturalSize ? naturalSize.height * scale : 360;

  const handleStageClick = (e: KonvaEventObject<MouseEvent | TouchEvent>) => {
    const stage = e.target.getStage();
    const pos = stage?.getPointerPosition();
    if (!pos) return;
    setPoints((prev) => [...prev, [pos.x, pos.y]]);
  };

  const handlePointDragMove = (index: number, e: KonvaEventObject<DragEvent>) => {
    const { x, y } = e.target.position();
    setPoints((prev) => prev.map((p, i) => (i === index ? [x, y] : p)));
  };

  const readyToSubmit = points.length >= 3;

  const handleSubmit = () => {
    if (!readyToSubmit) return;
    const polygon = points.map(([x, y]): Point => [x / scale, y / scale]);
    onSubmit(polygon);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex flex-col gap-4 items-center w-full max-w-[720px] bg-white rounded-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-medium">Wybierz obszar ROI</h2>
        <p className="text-sm text-gray-500 text-center max-w-md">
          Zaznacz co najmniej 3 punkty tworzące wielokąt obszaru zainteresowania (ROI).
        </p>

        {!frameImage && <p>⏳ Wczytywanie klatki wideo...</p>}

        {frameImage && naturalSize && (
          <Stage
            width={stageWidth}
            height={stageHeight}
            onClick={handleStageClick}
            onTap={handleStageClick}
            className="border border-gray-300 rounded"
          >
            <Layer>
              <KonvaImage image={frameImage} width={stageWidth} height={stageHeight} />
              {points.length > 1 && (
                <Line
                  points={points.flatMap(([x, y]) => [x, y])}
                  stroke={POINT_COLOR}
                  strokeWidth={2}
                  closed={points.length >= 3}
                />
              )}
              {points.map(([x, y], i) => (
                <Fragment key={i}>
                  <Circle
                    x={x}
                    y={y}
                    radius={7}
                    fill={POINT_COLOR}
                    stroke="white"
                    strokeWidth={2}
                    draggable
                    onDragMove={(e) => handlePointDragMove(i, e)}
                  />
                  <Text x={x + 10} y={y - 20} text={String(i + 1)} fill={POINT_COLOR} fontSize={16} fontStyle="bold" />
                </Fragment>
              ))}
            </Layer>
          </Stage>
        )}

        <button
          type="button"
          onClick={() => setPoints([])}
          disabled={points.length === 0}
          className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Wyczyść punkty
        </button>

        <div className="flex flex-row gap-2">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!readyToSubmit}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Zatwierdź obszar
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
          >
            Anuluj
          </button>
        </div>
      </div>
    </div>
  );
}
