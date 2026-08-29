import type { HeatmapVisualizerRequest } from '../types';

export interface VisualizerFieldsValue {
  fixedMax: string;
  alpha: string;
  sigma: string;
}

export const EMPTY_VISUALIZER_FIELDS: VisualizerFieldsValue = { fixedMax: '', alpha: '', sigma: '' };

function filledCount(value: VisualizerFieldsValue): number {
  return [value.fixedMax, value.alpha, value.sigma].filter((v) => v !== '').length;
}

export function isVisualizerFieldsValid(value: VisualizerFieldsValue): boolean {
  const count = filledCount(value);
  const complete = count === 0 || count === 3;
  const numbersValid =
    count !== 3 ||
    (Number(value.fixedMax) >= 0 &&
      Number(value.alpha) >= 0 &&
      Number(value.alpha) <= 1 &&
      Number(value.sigma) >= 0);
  return complete && numbersValid;
}

export function buildVisualizerRequest(value: VisualizerFieldsValue): HeatmapVisualizerRequest | undefined {
  if (filledCount(value) !== 3) return undefined;
  return { fixed_max: Number(value.fixedMax), alpha: Number(value.alpha), sigma: Number(value.sigma) };
}
