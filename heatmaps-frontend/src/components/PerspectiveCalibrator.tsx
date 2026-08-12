import { Fragment, useEffect, useState } from 'react';
import { Stage, Layer, Image as KonvaImage, Circle, Line, Text } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';
import type { Point } from '../types';

const STAGE_MAX_WIDTH = 640;
const POINT_COLOR = '#22c55e';
const inputClasses = 'border border-gray-300 rounded px-2 py-1 w-24';

interface PerspectiveCalibratorProps {
  videoUrl: string;
  onSubmit: (cameraPoints: Point[], realWorldPoints: Point[]) => void;
  onSkip: () => void;
  error?: string | null;
}

/** Grabs a static frame from the uploaded video and lets the user mark a
 * 4-point polygon on it, then collects the matching real-world coordinates
 * for each point — sent to the backend to compute the perspective
 * transformation matrix for this video. */
export function PerspectiveCalibrator({ videoUrl, onSubmit, onSkip, error }: PerspectiveCalibratorProps) {
  const [frameImage, setFrameImage] = useState<HTMLImageElement | null>(null);
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [realWorldInputs, setRealWorldInputs] = useState<[string, string][]>([
    ['', ''],
    ['', ''],
    ['', ''],
    ['', ''],
  ]);

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
    if (points.length >= 4) return;
    const stage = e.target.getStage();
    const pos = stage?.getPointerPosition();
    if (!pos) return;
    setPoints((prev) => [...prev, [pos.x, pos.y]]);
  };

  const handlePointDragMove = (index: number, e: KonvaEventObject<DragEvent>) => {
    const { x, y } = e.target.position();
    setPoints((prev) => prev.map((p, i) => (i === index ? [x, y] : p)));
  };

  const updateRealWorld = (index: number, axis: 0 | 1, value: string) => {
    setRealWorldInputs((prev) =>
      prev.map((pair, i) => (i === index ? (axis === 0 ? [value, pair[1]] : [pair[0], value]) : pair)),
    );
  };

  const realWorldComplete = realWorldInputs.every(
    ([x, y]) => x !== '' && y !== '' && !Number.isNaN(Number(x)) && !Number.isNaN(Number(y)),
  );
  const readyToSubmit = points.length === 4 && realWorldComplete;

  const handleSubmit = () => {
    if (!readyToSubmit) return;
    const cameraPoints: Point[] = points.map(([x, y]) => [x / scale, y / scale]);
    const realWorldPoints: Point[] = realWorldInputs.map(([x, y]) => [Number(x), Number(y)]);
    onSubmit(cameraPoints, realWorldPoints);
  };

  return (
    <div className="flex flex-col gap-4 items-center w-full max-w-[720px]">
      <h2 className="text-xl font-medium">Kalibracja perspektywy</h2>
      <p className="text-sm text-gray-500 text-center max-w-md">
        Zaznacz 4 punkty na klatce wideo tworzące czworokąt, a następnie podaj odpowiadające im rzeczywiste
        współrzędne (w metrach), w tej samej kolejności.
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
              <Line points={points.flat()} stroke={POINT_COLOR} strokeWidth={2} closed={points.length === 4} />
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

      {points.length === 4 && (
        <div className="flex flex-col gap-2 border border-gray-300 rounded-lg p-4 w-full max-w-105 items-center">
          <h3 className="text-lg font-semibold">Rzeczywiste współrzędne (m)</h3>
          {realWorldInputs.map(([x, y], i) => (
            <div key={i} className="flex flex-row items-center gap-3">
              <span className="w-6 text-sm text-gray-500">#{i + 1}</span>
              <label className="flex flex-col gap-1">
                X
                <input
                  type="number"
                  step="0.1"
                  value={x}
                  onChange={(e) => updateRealWorld(i, 0, e.target.value)}
                  className={inputClasses}
                />
              </label>
              <label className="flex flex-col gap-1">
                Y
                <input
                  type="number"
                  step="0.1"
                  value={y}
                  onChange={(e) => updateRealWorld(i, 1, e.target.value)}
                  className={inputClasses}
                />
              </label>
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-red-600">❌ {error}</p>}

      <div className="flex flex-row gap-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!readyToSubmit}
          className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Zatwierdź kalibrację
        </button>
        <button
          type="button"
          onClick={onSkip}
          className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
        >
          Pomiń kalibrację
        </button>
      </div>
    </div>
  );
}
