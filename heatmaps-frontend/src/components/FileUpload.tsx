interface FileUploadProps {
  onUpload: (file: File) => void;
  disabled?: boolean;
}

export function FileUpload({ onUpload, disabled }: FileUploadProps) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem('video') as HTMLInputElement;
    const file = input.files?.[0];
    if (file) onUpload(file);
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
      <button type="submit" disabled={disabled}>
        Wyślij
      </button>
    </form>
  );
}
