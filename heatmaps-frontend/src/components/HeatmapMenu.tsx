import { useEffect, useState } from 'react';
import { DIRECTIONS, REGION_BUCKETS, type VisualizerDefaultsResponse } from '../types';
import type { Direction, HeatmapRequest, Point, RegionBucket } from '../types';
import { getVisualizerDefaults } from "../api/client.ts";
import { TripwirePicker } from './TripwirePicker';
import { RoiPicker } from './RoiPicker';

type Category = 'directional' | 'speed' | 'cluster' | 'tripwire' | 'roi';

const CATEGORY_LABELS: Record<Category, string> = {
  directional: 'Kierunek',
  speed: 'Prędkość',
  cluster: 'Grupy',
  tripwire: 'Tripwire',
  roi: 'ROI',
};

const REGION_BUCKET_LABELS: Record<RegionBucket, string> = {
  inside: 'Wewnątrz',
  outside: 'Na zewnątrz',
  'outside->inside': 'Wejście',
  'inside->outside': 'Wyjście',
};

const inputClasses = 'border border-gray-300 rounded px-2 py-1 min-w-24';
const visualizerInputClasses = 'border border-gray-300 rounded px-2 py-1 w-full min-w-0';

interface HeatmapMenuProps {
  videoUrl: string;
  onAdd: (request: HeatmapRequest, customName?: string) => void;
}

export function HeatmapMenu({ videoUrl, onAdd }: HeatmapMenuProps) {
  const [category, setCategory] = useState<Category>('directional');
  const [direction, setDirection] = useState<Direction>('all');
  const [minSpeed, setMinSpeed] = useState('');
  const [maxSpeed, setMaxSpeed] = useState('');
  const [groupSize, setGroupSize] = useState('2');
  const [tripwireBucket, setTripwireBucket] = useState<RegionBucket>('inside');
  const [tripwirePoints, setTripwirePoints] = useState<{ p1: Point; p2: Point; insidePoint: Point } | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [roiBucket, setRoiBucket] = useState<RegionBucket>('inside');
  const [roiPolygon, setRoiPolygon] = useState<Point[] | null>(null);
  const [roiPickerOpen, setRoiPickerOpen] = useState(false);
  const [halfLifeTime, setHalfLifeTime] = useState('');
  const [customName, setCustomName] = useState('');
  const [fixedMax, setFixedMax] = useState('');
  const [alpha, setAlpha] = useState('');
  const [sigma, setSigma] = useState('');
  const [visualizerDefaults, setVisualizerDefaults] = useState({} as VisualizerDefaultsResponse);

  useEffect(() => {
    getVisualizerDefaults().then((res) => setVisualizerDefaults(res))
  }, []);

  const groupSizeValid = Number.isInteger(Number(groupSize)) && Number(groupSize) >= 2;
  const halfLifeTimeValid =
    halfLifeTime === '' || (Number.isInteger(Number(halfLifeTime)) && Number(halfLifeTime) > 0);

  const visualizerFilledCount = [fixedMax, alpha, sigma].filter((v) => v !== '').length;
  const visualizerComplete = visualizerFilledCount === 0 || visualizerFilledCount === 3;
  const visualizerNumbersValid =
    visualizerFilledCount !== 3 ||
    (Number(fixedMax) >= 0 && Number(alpha) >= 0 && Number(alpha) <= 1 && Number(sigma) >= 0);
  const visualizerValid = visualizerComplete && visualizerNumbersValid;
  const visualizer =
    visualizerFilledCount === 3
      ? { fixed_max: Number(fixedMax), alpha: Number(alpha), sigma: Number(sigma) }
      : undefined;

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmedName = customName.trim() || undefined;
    setCustomName('');

    if (category === 'directional') {
      onAdd(
        {
          type: 'directional',
          direction,
          ...(halfLifeTime !== '' ? { half_life_time: Number(halfLifeTime) } : {}),
          ...(visualizer ? { visualizer } : {}),
        },
        trimmedName,
      );
      return;
    }

    if (category === 'speed') {
      onAdd(
        {
          type: 'speed',
          ...(minSpeed !== '' ? { min_speed: Number(minSpeed) } : {}),
          ...(maxSpeed !== '' ? { max_speed: Number(maxSpeed) } : {}),
          ...(halfLifeTime !== '' ? { half_life_time: Number(halfLifeTime) } : {}),
          ...(visualizer ? { visualizer } : {}),
        },
        trimmedName,
      );
      return;
    }

    if (category === 'tripwire') {
      if (!tripwirePoints) return;
      onAdd(
        {
          type: 'tripwire',
          p1: tripwirePoints.p1,
          p2: tripwirePoints.p2,
          inside_point: tripwirePoints.insidePoint,
          bucket: tripwireBucket,
          ...(halfLifeTime !== '' ? { half_life_time: Number(halfLifeTime) } : {}),
          ...(visualizer ? { visualizer } : {}),
        },
        trimmedName,
      );
      return;
    }

    if (category === 'roi') {
      if (!roiPolygon) return;
      onAdd(
        {
          type: 'roi',
          polygon: roiPolygon,
          bucket: roiBucket,
          ...(halfLifeTime !== '' ? { half_life_time: Number(halfLifeTime) } : {}),
          ...(visualizer ? { visualizer } : {}),
        },
        trimmedName,
      );
      return;
    }

    if (groupSizeValid) {
      onAdd(
        {
          type: 'cluster',
          group_size: Number(groupSize),
          ...(halfLifeTime !== '' ? { half_life_time: Number(halfLifeTime) } : {}),
          ...(visualizer ? { visualizer } : {}),
        },
        trimmedName,
      );
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-4 border border-gray-300 rounded-lg p-4 w-full max-w-125"
    >
      <h3 className="text-lg font-semibold">Dodaj analizę heatmapy</h3>

      <label className="flex flex-col gap-1">
        Nazwa (opcjonalnie)
        <input
          type="text"
          value={customName}
          onChange={(e) => setCustomName(e.target.value)}
          placeholder="automatyczna"
          className={inputClasses}
        />
      </label>

      <fieldset className="border-0 p-0 flex gap-4">
        {(Object.keys(CATEGORY_LABELS) as Category[]).map((value) => (
          <label key={value} className="flex items-center gap-1">
            <input
              type="radio"
              name="category"
              value={value}
              checked={category === value}
              onChange={() => setCategory(value)}
            />
            {CATEGORY_LABELS[value]}
          </label>
        ))}
      </fieldset>

      {category === 'directional' && (
        <fieldset className="border-0 p-0 flex gap-3 flex-wrap">
          {DIRECTIONS.map((value) => (
            <label key={value} className="flex items-center gap-1">
              <input
                type="radio"
                name="direction"
                value={value}
                checked={direction === value}
                onChange={() => setDirection(value)}
              />
              {value}
            </label>
          ))}
        </fieldset>
      )}

      {category === 'speed' && (
        <div className="flex flex-row gap-4">
          <label className="flex flex-col gap-1 min-w-24">
            Min (km/h)
            <input
              type="number"
              min={0}
              step="0.1"
              value={minSpeed}
              onChange={(e) => setMinSpeed(e.target.value)}
              placeholder="brak"
              className={inputClasses}
            />
          </label>
          <label className="flex flex-col gap-1 min-w-24">
            Max (km/h)
            <input
              type="number"
              min={0}
              step="0.1"
              value={maxSpeed}
              onChange={(e) => setMaxSpeed(e.target.value)}
              placeholder="brak"
              className={inputClasses}
            />
          </label>
        </div>
      )}

      {category === 'cluster' && (
        <label className="flex flex-col gap-1 max-w-[160px]">
          Liczba osób w grupie
          <input
            type="number"
            min={2}
            step="1"
            value={groupSize}
            onChange={(e) => setGroupSize(e.target.value)}
            className={inputClasses}
          />
        </label>
      )}

      {category === 'tripwire' && (
        <div className="flex flex-col gap-3">
          <fieldset className="border-0 p-0 flex gap-3 flex-wrap">
            {REGION_BUCKETS.map((value) => (
              <label key={value} className="flex items-center gap-1">
                <input
                  type="radio"
                  name="tripwireBucket"
                  value={value}
                  checked={tripwireBucket === value}
                  onChange={() => setTripwireBucket(value)}
                />
                {REGION_BUCKET_LABELS[value]}
              </label>
            ))}
          </fieldset>

          {tripwirePoints ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">Punkty tripwire ustawione</span>
              <button
                type="button"
                onClick={() => setPickerOpen(true)}
                className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
              >
                Zmień punkty
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setPickerOpen(true)}
              className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 self-start"
            >
              Wybierz punkty na wideo
            </button>
          )}
        </div>
      )}

      {category === 'roi' && (
        <div className="flex flex-col gap-3">
          <fieldset className="border-0 p-0 flex gap-3 flex-wrap">
            {REGION_BUCKETS.map((value) => (
              <label key={value} className="flex items-center gap-1">
                <input
                  type="radio"
                  name="roiBucket"
                  value={value}
                  checked={roiBucket === value}
                  onChange={() => setRoiBucket(value)}
                />
                {REGION_BUCKET_LABELS[value]}
              </label>
            ))}
          </fieldset>

          {roiPolygon ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">Obszar ROI ustawiony ({roiPolygon.length} pkt.)</span>
              <button
                type="button"
                onClick={() => setRoiPickerOpen(true)}
                className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
              >
                Zmień obszar
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setRoiPickerOpen(true)}
              className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 self-start"
            >
              Wybierz obszar na wideo
            </button>
          )}
        </div>
      )}

      {pickerOpen && (
        <TripwirePicker
          videoUrl={videoUrl}
          initial={tripwirePoints}
          onSubmit={(p1, p2, insidePoint) => {
            setTripwirePoints({ p1, p2, insidePoint });
            setPickerOpen(false);
          }}
          onCancel={() => setPickerOpen(false)}
        />
      )}

      {roiPickerOpen && (
        <RoiPicker
          videoUrl={videoUrl}
          initial={roiPolygon}
          onSubmit={(polygon) => {
            setRoiPolygon(polygon);
            setRoiPickerOpen(false);
          }}
          onCancel={() => setRoiPickerOpen(false)}
        />
      )}

      <label className="flex flex-col gap-1 min-w-24 max-w-[160px]">
        Czas połowicznego zaniku (s)
        <input
          type="number"
          min={1}
          step="1"
          value={halfLifeTime}
          onChange={(e) => setHalfLifeTime(e.target.value)}
          placeholder="brak"
          className={inputClasses}
        />
      </label>

      <fieldset className="border-0 p-0 flex flex-col gap-2">
        <legend className="text-sm text-gray-500 pt-4">Ustawienia wizualizacji (opcjonalnie)</legend>
        <div className="flex flex-row flex-wrap gap-3">
          <label className="flex flex-col gap-1 flex-1 min-w-20">
            Fixed max
            <input
              type="number"
              min={0}
              step="0.1"
              value={fixedMax}
              onChange={(e) => setFixedMax(e.target.value)}
              placeholder={visualizerDefaults?.fixed_max?.toString() ?? 'automatycznie'}
              className={visualizerInputClasses}
            />
          </label>
          <label className="flex flex-col gap-1 flex-1 min-w-20">
            Alpha
            <input
              type="number"
              min={0}
              max={1}
              step="0.05"
              value={alpha}
              onChange={(e) => setAlpha(e.target.value)}
              placeholder={visualizerDefaults?.alpha?.toString() ?? 'automatycznie'}
              className={visualizerInputClasses}
            />
          </label>
          <label className="flex flex-col gap-1 flex-1 min-w-20">
            Sigma
            <input
              type="number"
              min={0}
              step="1"
              value={sigma}
              onChange={(e) => setSigma(e.target.value)}
              placeholder={visualizerDefaults?.sigma?.toString() ?? 'automatycznie'}
              className={visualizerInputClasses}
            />
          </label>
        </div>
        {!visualizerComplete && (
          <p className="text-red-600 text-sm">Uzupełnij wszystkie trzy pola albo zostaw je puste.</p>
        )}
      </fieldset>

      <button
        type="submit"
        disabled={
          (category === 'cluster' && !groupSizeValid) ||
          (category === 'tripwire' && !tripwirePoints) ||
          (category === 'roi' && !roiPolygon) ||
          !visualizerValid ||
          !halfLifeTimeValid
        }
        className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Dodaj
      </button>
    </form>
  );
}
