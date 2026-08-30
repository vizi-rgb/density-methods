import { useState } from 'react';
import type { HeatmapJobRequest, View } from '../types';
import { PrimitiveHeatmapFields } from './PrimitiveHeatmapFields';
import {
  EMPTY_PRIMITIVE_FIELDS,
  buildPrimitiveRequest,
  isPrimitiveFieldsValid,
  type PrimitiveFieldsValue,
} from '../utils/primitiveHeatmapFields';
import { HeatmapComposer } from './HeatmapComposer';

type Mode = 'simple' | 'composed';

const inputClasses = 'border border-gray-300 rounded px-2 py-1 min-w-24';
const modeButtonClasses =
  'inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50';

const VIEW_LABELS: Record<View, string> = {
  camera: 'Widok kamery',
  world: 'Widok z góry (world)',
};

interface HeatmapMenuProps {
  videoUrl: string;
  calibrated: boolean;
  onAdd: (request: HeatmapJobRequest, customName?: string) => void;
}

export function HeatmapMenu({ videoUrl, calibrated, onAdd }: HeatmapMenuProps) {
  const [view, setView] = useState<View>('camera');
  const [mode, setMode] = useState<Mode>('simple');
  const [fields, setFields] = useState<PrimitiveFieldsValue>(EMPTY_PRIMITIVE_FIELDS);
  const [customName, setCustomName] = useState('');

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const request = buildPrimitiveRequest(fields, true);
    if (!request) return;
    const trimmedName = customName.trim() || undefined;
    setCustomName('');
    onAdd({ ...request, view }, trimmedName);
  };

  return (
    <div className="flex flex-col gap-4 border border-gray-300 rounded-lg p-4 w-full max-w-125">
      <h3 className="text-lg font-semibold">Dodaj analizę heatmapy</h3>

      <div className="flex flex-col gap-1">
        <fieldset className="border-0 p-0 flex gap-2">
          {(Object.keys(VIEW_LABELS) as View[]).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setView(option)}
              className={`${modeButtonClasses} ${view === option ? 'bg-gray-100 font-semibold' : ''}`}
            >
              {VIEW_LABELS[option]}
            </button>
          ))}
        </fieldset>
        {view === 'world' && !calibrated && (
          <p className="text-sm text-amber-600">
            ⚠️ To wideo nie zostało skalibrowane — widok z góry użyje ogólnej skali referencyjnej.
          </p>
        )}
      </div>

      <fieldset className="border-0 p-0 flex gap-2">
        <button
          type="button"
          onClick={() => setMode('simple')}
          className={`${modeButtonClasses} ${mode === 'simple' ? 'bg-gray-100 font-semibold' : ''}`}
        >
          Pojedynczy warunek
        </button>
        <button
          type="button"
          onClick={() => setMode('composed')}
          className={`${modeButtonClasses} ${mode === 'composed' ? 'bg-gray-100 font-semibold' : ''}`}
        >
          Zestaw warunków (AND/OR/NOT)
        </button>
      </fieldset>

      {mode === 'simple' ? (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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

          <PrimitiveHeatmapFields videoUrl={videoUrl} value={fields} onChange={setFields} />

          <button
            type="submit"
            disabled={!isPrimitiveFieldsValid(fields, true)}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Dodaj
          </button>
        </form>
      ) : (
        <HeatmapComposer videoUrl={videoUrl} view={view} onAdd={onAdd} />
      )}
    </div>
  );
}
