import { useState } from 'react';
import { HEATMAP_TYPES } from '../types';
import type { HeatmapType } from '../types';

interface FileUploadProps {
  onUpload: (file: File, heatmapTypes: HeatmapType[]) => void;
  disabled?: boolean;
}

export function FileUpload({ onUpload, disabled }: FileUploadProps) {
  const [selectedTypes, setSelectedTypes] = useState<HeatmapType[]>([]);

  const toggleType = (type: HeatmapType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem('video') as HTMLInputElement;
    const file = input.files?.[0];
    if (file && selectedTypes.length > 0) onUpload(file, selectedTypes);
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
      <h2>Prześlij wideo do analizy</h2>
      <input
        name="video"
        type="file"
        accept="video/*"
        required
        disabled={disabled}
      />
      <fieldset style={{ border: '1px solid #ccc', borderRadius: '4px', padding: '0.75rem 1rem' }}>
        <legend>Typy heatmapy</legend>
        {HEATMAP_TYPES.map(({ value, label }) => (
          <label key={value} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <input
              type="checkbox"
              checked={selectedTypes.includes(value)}
              onChange={() => toggleType(value)}
              disabled={disabled}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <button type="submit" disabled={disabled || selectedTypes.length === 0}>
        Wyślij
      </button>
    </form>
  );
}
