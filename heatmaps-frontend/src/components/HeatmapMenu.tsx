import { useState } from 'react';
import { DIRECTIONS } from '../types';
import type { Direction, HeatmapRequest } from '../types';

type Category = 'directional' | 'speed' | 'cluster';

const CATEGORY_LABELS: Record<Category, string> = {
  directional: 'Kierunek',
  speed: 'Prędkość',
  cluster: 'Grupy',
};

const inputClasses = 'border border-gray-300 rounded px-2 py-1 min-w-24';
const visualizerInputClasses = 'border border-gray-300 rounded px-2 py-1 w-full min-w-0';

interface HeatmapMenuProps {
  onAdd: (request: HeatmapRequest, customName?: string) => void;
}

export function HeatmapMenu({ onAdd }: HeatmapMenuProps) {
  const [category, setCategory] = useState<Category>('directional');
  const [direction, setDirection] = useState<Direction>('all');
  const [minSpeed, setMinSpeed] = useState('');
  const [maxSpeed, setMaxSpeed] = useState('');
  const [groupSize, setGroupSize] = useState('2');
  const [customName, setCustomName] = useState('');
  const [fixedMax, setFixedMax] = useState('');
  const [alpha, setAlpha] = useState('');
  const [sigma, setSigma] = useState('');

  const groupSizeValid = Number.isInteger(Number(groupSize)) && Number(groupSize) >= 2;

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
      onAdd({ type: 'directional', direction, ...(visualizer ? { visualizer } : {}) }, trimmedName);
      return;
    }

    if (category === 'speed') {
      onAdd(
        {
          type: 'speed',
          ...(minSpeed !== '' ? { min_speed: Number(minSpeed) } : {}),
          ...(maxSpeed !== '' ? { max_speed: Number(maxSpeed) } : {}),
          ...(visualizer ? { visualizer } : {}),
        },
        trimmedName,
      );
      return;
    }

    if (groupSizeValid) {
      onAdd(
        { type: 'cluster', group_size: Number(groupSize), ...(visualizer ? { visualizer } : {}) },
        trimmedName,
      );
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-4 border border-gray-300 rounded-lg p-4 w-full max-w-105"
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
              placeholder="domyślne"
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
              placeholder="domyślne"
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
              placeholder="domyślne"
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
        disabled={(category === 'cluster' && !groupSizeValid) || !visualizerValid}
        className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Dodaj
      </button>
    </form>
  );
}
