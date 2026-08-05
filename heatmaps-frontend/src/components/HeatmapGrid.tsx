import { HeatmapTile } from './HeatmapTile';
import type { HeatmapTileData } from '../types';
import {cn} from "@sglara/cn";

interface HeatmapGridProps {
  tiles: HeatmapTileData[];
  layout: 'grid' | 'list';
  editMode: 'normal' | 'edit';
  onDelete: (jobId: string) => void;
}

export function HeatmapGrid({ tiles, layout, editMode, onDelete }: HeatmapGridProps) {
  if (tiles.length === 0) {
    return (
      <p className="text-gray-500 text-center">
        Brak analiz — użyj menu powyżej, aby dodać pierwszą.
      </p>
    );
  }

  const containerClasses = cn(
      layout === 'grid'
          ? 'grid grid-cols-[repeat(auto-fill,minmax(360px,1fr))] gap-4 w-full'
          : 'flex flex-col gap-4 w-full',

  )

  return (
    <div className={containerClasses}>
      {tiles.map((tile) => (
        <HeatmapTile key={tile.jobId} jobId={tile.jobId} label={tile.label} editMode={editMode} onDelete={onDelete} />
      ))}
    </div>
  );
}
