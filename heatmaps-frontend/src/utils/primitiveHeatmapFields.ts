import type { Direction, HeatmapRequest, Point, RegionBucket } from '../types';
import { EMPTY_VISUALIZER_FIELDS, buildVisualizerRequest, isVisualizerFieldsValid, type VisualizerFieldsValue } from './visualizerFields';

export type Category = 'directional' | 'speed' | 'cluster' | 'tripwire' | 'roi';

export const CATEGORY_LABELS: Record<Category, string> = {
  directional: 'Kierunek',
  speed: 'Prędkość',
  cluster: 'Grupy',
  tripwire: 'Tripwire',
  roi: 'ROI',
};

export interface PrimitiveFieldsValue {
  category: Category;
  direction: Direction;
  minSpeed: string;
  maxSpeed: string;
  groupSize: string;
  tripwireBucket: RegionBucket;
  tripwirePoints: { p1: Point; p2: Point; insidePoint: Point } | null;
  roiBucket: RegionBucket;
  roiPolygon: Point[] | null;
  halfLifeTime: string;
  visualizer: VisualizerFieldsValue;
}

export const EMPTY_PRIMITIVE_FIELDS: PrimitiveFieldsValue = {
  category: 'directional',
  direction: 'all',
  minSpeed: '',
  maxSpeed: '',
  groupSize: '2',
  tripwireBucket: 'inside',
  tripwirePoints: null,
  roiBucket: 'inside',
  roiPolygon: null,
  halfLifeTime: '',
  visualizer: EMPTY_VISUALIZER_FIELDS,
};

function isGroupSizeValid(groupSize: string): boolean {
  return Number.isInteger(Number(groupSize)) && Number(groupSize) >= 2;
}

function isHalfLifeTimeValid(halfLifeTime: string): boolean {
  return halfLifeTime === '' || (Number.isInteger(Number(halfLifeTime)) && Number(halfLifeTime) > 0);
}

export function isPrimitiveFieldsValid(value: PrimitiveFieldsValue, showVisualizer: boolean): boolean {
  const categoryValid =
    value.category === 'cluster'
      ? isGroupSizeValid(value.groupSize)
      : value.category === 'tripwire'
        ? value.tripwirePoints !== null
        : value.category === 'roi'
          ? value.roiPolygon !== null
          : true;

  return (
    categoryValid &&
    isHalfLifeTimeValid(value.halfLifeTime) &&
    (!showVisualizer || isVisualizerFieldsValid(value.visualizer))
  );
}

export function buildPrimitiveRequest(value: PrimitiveFieldsValue, showVisualizer: boolean): HeatmapRequest | null {
  if (!isPrimitiveFieldsValid(value, showVisualizer)) return null;

  const halfLifeTime = value.halfLifeTime !== '' ? Number(value.halfLifeTime) : undefined;
  const visualizer = showVisualizer ? buildVisualizerRequest(value.visualizer) : undefined;

  if (value.category === 'directional') {
    return {
      type: 'directional',
      direction: value.direction,
      ...(halfLifeTime !== undefined ? { half_life_time: halfLifeTime } : {}),
      ...(visualizer ? { visualizer } : {}),
    };
  }

  if (value.category === 'speed') {
    return {
      type: 'speed',
      ...(value.minSpeed !== '' ? { min_speed: Number(value.minSpeed) } : {}),
      ...(value.maxSpeed !== '' ? { max_speed: Number(value.maxSpeed) } : {}),
      ...(halfLifeTime !== undefined ? { half_life_time: halfLifeTime } : {}),
      ...(visualizer ? { visualizer } : {}),
    };
  }

  if (value.category === 'tripwire') {
    if (!value.tripwirePoints) return null;
    return {
      type: 'tripwire',
      p1: value.tripwirePoints.p1,
      p2: value.tripwirePoints.p2,
      inside_point: value.tripwirePoints.insidePoint,
      bucket: value.tripwireBucket,
      ...(halfLifeTime !== undefined ? { half_life_time: halfLifeTime } : {}),
      ...(visualizer ? { visualizer } : {}),
    };
  }

  if (value.category === 'roi') {
    if (!value.roiPolygon) return null;
    return {
      type: 'roi',
      polygon: value.roiPolygon,
      bucket: value.roiBucket,
      ...(halfLifeTime !== undefined ? { half_life_time: halfLifeTime } : {}),
      ...(visualizer ? { visualizer } : {}),
    };
  }

  return {
    type: 'cluster',
    group_size: Number(value.groupSize),
    ...(halfLifeTime !== undefined ? { half_life_time: halfLifeTime } : {}),
    ...(visualizer ? { visualizer } : {}),
  };
}
