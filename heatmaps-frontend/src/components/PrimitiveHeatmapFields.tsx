import { useState } from 'react';
import { DIRECTIONS, REGION_BUCKETS } from '../types';
import type { RegionBucket } from '../types';
import { TripwirePicker } from './TripwirePicker';
import { RoiPicker } from './RoiPicker';
import { VisualizerFields } from './VisualizerFields';
import { CATEGORY_LABELS, type Category, type PrimitiveFieldsValue } from '../utils/primitiveHeatmapFields';

const REGION_BUCKET_LABELS: Record<RegionBucket, string> = {
  inside: 'Wewnątrz',
  outside: 'Na zewnątrz',
  'outside->inside': 'Wejście',
  'inside->outside': 'Wyjście',
};

const inputClasses = 'border border-gray-300 rounded px-2 py-1 min-w-24';

interface PrimitiveHeatmapFieldsProps {
  videoUrl: string;
  value: PrimitiveFieldsValue;
  onChange: (value: PrimitiveFieldsValue) => void;
  showVisualizer?: boolean;
}

export function PrimitiveHeatmapFields({
  videoUrl,
  value,
  onChange,
  showVisualizer = true,
}: PrimitiveHeatmapFieldsProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [roiPickerOpen, setRoiPickerOpen] = useState(false);

  return (
    <>
      <fieldset className="border-0 p-0 flex gap-4">
        {(Object.keys(CATEGORY_LABELS) as Category[]).map((category) => (
          <label key={category} className="flex items-center gap-1">
            <input
              type="radio"
              name="category"
              value={category}
              checked={value.category === category}
              onChange={() => onChange({ ...value, category })}
            />
            {CATEGORY_LABELS[category]}
          </label>
        ))}
      </fieldset>

      {value.category === 'directional' && (
        <fieldset className="border-0 p-0 flex gap-3 flex-wrap">
          {DIRECTIONS.map((direction) => (
            <label key={direction} className="flex items-center gap-1">
              <input
                type="radio"
                name="direction"
                value={direction}
                checked={value.direction === direction}
                onChange={() => onChange({ ...value, direction })}
              />
              {direction}
            </label>
          ))}
        </fieldset>
      )}

      {value.category === 'speed' && (
        <div className="flex flex-row gap-4">
          <label className="flex flex-col gap-1 min-w-24">
            Min (km/h)
            <input
              type="number"
              min={0}
              step="0.1"
              value={value.minSpeed}
              onChange={(e) => onChange({ ...value, minSpeed: e.target.value })}
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
              value={value.maxSpeed}
              onChange={(e) => onChange({ ...value, maxSpeed: e.target.value })}
              placeholder="brak"
              className={inputClasses}
            />
          </label>
        </div>
      )}

      {value.category === 'cluster' && (
        <label className="flex flex-col gap-1 max-w-[160px]">
          Liczba osób w grupie
          <input
            type="number"
            min={2}
            step="1"
            value={value.groupSize}
            onChange={(e) => onChange({ ...value, groupSize: e.target.value })}
            className={inputClasses}
          />
        </label>
      )}

      {value.category === 'tripwire' && (
        <div className="flex flex-col gap-3">
          <fieldset className="border-0 p-0 flex gap-3 flex-wrap">
            {REGION_BUCKETS.map((bucket) => (
              <label key={bucket} className="flex items-center gap-1">
                <input
                  type="radio"
                  name="tripwireBucket"
                  value={bucket}
                  checked={value.tripwireBucket === bucket}
                  onChange={() => onChange({ ...value, tripwireBucket: bucket })}
                />
                {REGION_BUCKET_LABELS[bucket]}
              </label>
            ))}
          </fieldset>

          {value.tripwirePoints ? (
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

      {value.category === 'roi' && (
        <div className="flex flex-col gap-3">
          <fieldset className="border-0 p-0 flex gap-3 flex-wrap">
            {REGION_BUCKETS.map((bucket) => (
              <label key={bucket} className="flex items-center gap-1">
                <input
                  type="radio"
                  name="roiBucket"
                  value={bucket}
                  checked={value.roiBucket === bucket}
                  onChange={() => onChange({ ...value, roiBucket: bucket })}
                />
                {REGION_BUCKET_LABELS[bucket]}
              </label>
            ))}
          </fieldset>

          {value.roiPolygon ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">Obszar ROI ustawiony ({value.roiPolygon.length} pkt.)</span>
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
          initial={value.tripwirePoints}
          onSubmit={(p1, p2, insidePoint) => {
            onChange({ ...value, tripwirePoints: { p1, p2, insidePoint } });
            setPickerOpen(false);
          }}
          onCancel={() => setPickerOpen(false)}
        />
      )}

      {roiPickerOpen && (
        <RoiPicker
          videoUrl={videoUrl}
          initial={value.roiPolygon}
          onSubmit={(polygon) => {
            onChange({ ...value, roiPolygon: polygon });
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
          value={value.halfLifeTime}
          onChange={(e) => onChange({ ...value, halfLifeTime: e.target.value })}
          placeholder="brak"
          className={inputClasses}
        />
      </label>

      {showVisualizer && (
        <VisualizerFields
          value={value.visualizer}
          onChange={(visualizer) => onChange({ ...value, visualizer })}
        />
      )}
    </>
  );
}
