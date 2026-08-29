import { useState } from 'react';
import type { HeatmapJobRequest, HeatmapLayer, Operator } from '../types';
import { PrimitiveHeatmapFields } from './PrimitiveHeatmapFields';
import {
  EMPTY_PRIMITIVE_FIELDS,
  buildPrimitiveRequest,
  isPrimitiveFieldsValid,
  type PrimitiveFieldsValue,
} from '../utils/primitiveHeatmapFields';
import { VisualizerFields } from './VisualizerFields';
import {
  EMPTY_VISUALIZER_FIELDS,
  buildVisualizerRequest,
  isVisualizerFieldsValid,
  type VisualizerFieldsValue,
} from '../utils/visualizerFields';
import { describeComposedLayers, describeLayerCondition } from '../utils/describeComposedLayers';

const OPERATOR_LABELS: Record<Operator, string> = {
  AND: 'I (AND)',
  OR: 'LUB (OR)',
  AND_NOT: 'I NIE (AND NOT)',
};

const buttonClasses =
  'inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed';
const iconButtonClasses =
  'inline-flex items-center justify-center rounded-md border border-gray-300 w-7 h-7 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed';
const inputClasses = 'border border-gray-300 rounded px-2 py-1 min-w-24';

/** First layer never has an operator; every later layer needs one — fills
 * in a default when reordering/removal would otherwise leave one unset. */
function normalizeLayers(layers: HeatmapLayer[]): HeatmapLayer[] {
  return layers.map((layer, i) =>
    i === 0
      ? { ...layer, operator: undefined }
      : { ...layer, operator: layer.operator ?? 'AND' },
  );
}

interface HeatmapComposerProps {
  videoUrl: string;
  onAdd: (request: HeatmapJobRequest, customName?: string) => void;
}

export function HeatmapComposer({ videoUrl, onAdd }: HeatmapComposerProps) {
  const [layers, setLayers] = useState<HeatmapLayer[]>([]);
  const [pendingFields, setPendingFields] = useState<PrimitiveFieldsValue>(EMPTY_PRIMITIVE_FIELDS);
  const [pendingOperator, setPendingOperator] = useState<Operator>('AND');
  const [pendingInvert, setPendingInvert] = useState(false);
  const [visualizer, setVisualizer] = useState<VisualizerFieldsValue>(EMPTY_VISUALIZER_FIELDS);
  const [customName, setCustomName] = useState('');

  const handleAddLayer = () => {
    const request = buildPrimitiveRequest(pendingFields, false);
    if (!request) return;
    setLayers((prev) =>
      normalizeLayers([...prev, { heatmap: request, operator: pendingOperator, invert: pendingInvert }]),
    );
    setPendingFields(EMPTY_PRIMITIVE_FIELDS);
    setPendingOperator('AND');
    setPendingInvert(false);
  };

  const handleRemoveLayer = (index: number) => {
    setLayers((prev) => normalizeLayers(prev.filter((_, i) => i !== index)));
  };

  const handleMoveLayer = (index: number, delta: number) => {
    setLayers((prev) => {
      const target = index + delta;
      if (target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return normalizeLayers(next);
    });
  };

  const handleLayerOperatorChange = (index: number, operator: Operator) => {
    setLayers((prev) => prev.map((layer, i) => (i === index ? { ...layer, operator } : layer)));
  };

  const handleLayerInvertChange = (index: number, invert: boolean) => {
    setLayers((prev) => prev.map((layer, i) => (i === index ? { ...layer, invert } : layer)));
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmedName = customName.trim() || undefined;
    setCustomName('');
    const visualizerRequest = buildVisualizerRequest(visualizer);
    onAdd(
      { type: 'composed', layers, ...(visualizerRequest ? { visualizer: visualizerRequest } : {}) },
      trimmedName,
    );
    setLayers([]);
  };

  const canSubmit = layers.length >= 2 && isVisualizerFieldsValid(visualizer);

  return (
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

      {layers.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-sm text-gray-500">Warstwy (kolejność ma znaczenie)</span>
          {layers.map((layer, i) => (
            <div key={i} className="flex flex-col gap-2 border border-gray-300 rounded-md p-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-500 w-5">{i + 1}.</span>
                {i > 0 && (
                  <select
                    value={layer.operator ?? 'AND'}
                    onChange={(e) => handleLayerOperatorChange(i, e.target.value as Operator)}
                    className={inputClasses}
                  >
                    {(Object.keys(OPERATOR_LABELS) as Operator[]).map((operator) => (
                      <option key={operator} value={operator}>
                        {OPERATOR_LABELS[operator]}
                      </option>
                    ))}
                  </select>
                )}
                <span className="text-sm">
                  {layer.invert ? `NOT ${describeLayerCondition(layer.heatmap)}` : describeLayerCondition(layer.heatmap)}
                </span>
                <label className="flex items-center gap-1 text-sm ml-auto">
                  <input
                    type="checkbox"
                    checked={layer.invert ?? false}
                    onChange={(e) => handleLayerInvertChange(i, e.target.checked)}
                  />
                  NIE (odwróć)
                </label>
                <button
                  type="button"
                  onClick={() => handleMoveLayer(i, -1)}
                  disabled={i === 0}
                  className={iconButtonClasses}
                  aria-label="Przesuń w górę"
                >
                  ▲
                </button>
                <button
                  type="button"
                  onClick={() => handleMoveLayer(i, 1)}
                  disabled={i === layers.length - 1}
                  className={iconButtonClasses}
                  aria-label="Przesuń w dół"
                >
                  ▼
                </button>
                <button
                  type="button"
                  onClick={() => handleRemoveLayer(i)}
                  className="inline-flex items-center justify-center rounded-md border border-gray-300 w-7 h-7 text-sm hover:bg-gray-50 text-red-600"
                  aria-label="Usuń warstwę"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-sm italic text-gray-600 border border-gray-200 rounded-md p-2 bg-gray-50">
        {layers.length > 0 ? describeComposedLayers(layers) : 'Dodaj co najmniej dwie warstwy, aby zbudować zapytanie.'}
      </p>

      <fieldset className="border border-gray-300 rounded-lg p-3 flex flex-col gap-3">
        <legend className="text-sm text-gray-500 px-1">Dodaj warstwę</legend>

        {layers.length > 0 && (
          <div className="flex items-center gap-3 flex-wrap">
            <label className="flex items-center gap-2">
              Operator
              <select
                value={pendingOperator}
                onChange={(e) => setPendingOperator(e.target.value as Operator)}
                className={inputClasses}
              >
                {(Object.keys(OPERATOR_LABELS) as Operator[]).map((operator) => (
                  <option key={operator} value={operator}>
                    {OPERATOR_LABELS[operator]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={pendingInvert}
                onChange={(e) => setPendingInvert(e.target.checked)}
              />
              NIE (odwróć)
            </label>
          </div>
        )}

        <PrimitiveHeatmapFields
          videoUrl={videoUrl}
          value={pendingFields}
          onChange={setPendingFields}
          showVisualizer={false}
        />

        <button
          type="button"
          onClick={handleAddLayer}
          disabled={!isPrimitiveFieldsValid(pendingFields, false)}
          className={`${buttonClasses} self-start`}
        >
          Dodaj warstwę
        </button>
      </fieldset>

      <VisualizerFields value={visualizer} onChange={setVisualizer} />

      <button type="submit" disabled={!canSubmit} className={buttonClasses}>
        Dodaj złożoną analizę
      </button>
    </form>
  );
}
