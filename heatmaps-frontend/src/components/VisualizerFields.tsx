import { useEffect, useState } from 'react';
import type { VisualizerDefaultsResponse } from '../types';
import { getVisualizerDefaults } from '../api/client.ts';
import type { VisualizerFieldsValue } from '../utils/visualizerFields';

const visualizerInputClasses = 'border border-gray-300 rounded px-2 py-1 w-full min-w-0';

interface VisualizerFieldsProps {
  value: VisualizerFieldsValue;
  onChange: (value: VisualizerFieldsValue) => void;
}

export function VisualizerFields({ value, onChange }: VisualizerFieldsProps) {
  const [defaults, setDefaults] = useState({} as VisualizerDefaultsResponse);

  useEffect(() => {
    getVisualizerDefaults().then((res) => setDefaults(res));
  }, []);

  const filledCount = [value.fixedMax, value.alpha, value.sigma].filter((v) => v !== '').length;
  const complete = filledCount === 0 || filledCount === 3;

  return (
    <fieldset className="border-0 p-0 flex flex-col gap-2">
      <legend className="text-sm text-gray-500 pt-4">Ustawienia wizualizacji (opcjonalnie)</legend>
      <div className="flex flex-row flex-wrap gap-3">
        <label className="flex flex-col gap-1 flex-1 min-w-20">
          Fixed max
          <input
            type="number"
            min={0}
            step="0.1"
            value={value.fixedMax}
            onChange={(e) => onChange({ ...value, fixedMax: e.target.value })}
            placeholder={defaults?.fixed_max?.toString() ?? 'automatycznie'}
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
            value={value.alpha}
            onChange={(e) => onChange({ ...value, alpha: e.target.value })}
            placeholder={defaults?.alpha?.toString() ?? 'automatycznie'}
            className={visualizerInputClasses}
          />
        </label>
        <label className="flex flex-col gap-1 flex-1 min-w-20">
          Sigma
          <input
            type="number"
            min={0}
            step="1"
            value={value.sigma}
            onChange={(e) => onChange({ ...value, sigma: e.target.value })}
            placeholder={defaults?.sigma?.toString() ?? 'automatycznie'}
            className={visualizerInputClasses}
          />
        </label>
      </div>
      {!complete && (
        <p className="text-red-600 text-sm">Uzupełnij wszystkie trzy pola albo zostaw je puste.</p>
      )}
    </fieldset>
  );
}
