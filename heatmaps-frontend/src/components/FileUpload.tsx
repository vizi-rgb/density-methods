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
    <form onSubmit={handleSubmit} className="flex flex-col items-center gap-4">
      <h2 className="text-xl font-medium">Prześlij wideo do analizy</h2>
      <input
        name="video"
        type="file"
        accept="video/*"
        required
        disabled={disabled}
      />
      <button
        type="submit"
        disabled={disabled}
        className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Wyślij
      </button>
    </form>
  );
}
