from dataclasses import dataclass
from pathlib import Path

import cv2

@dataclass(frozen=True)
class DataSourceInfo:
    height: int
    width: int
    frames: int
    fps: int | None = None


class DataSourceInfoReader:
    _VIDEO_FILE_EXTENSION = ".mp4"

    def __init__(self, source_path: str | Path) -> None:
        self.source_path = Path(source_path)

    def read(self) -> DataSourceInfo:
        if not self.source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {self.source_path}")
        if self.source_path.is_dir():
            return self._from_directory(self.source_path)
        if self.source_path.is_file():
            return self._from_file(self.source_path)
        raise ValueError(f"Unsupported source path type: {self.source_path}")

    def _from_directory(self, directory: Path) -> DataSourceInfo:
        image_files = self._collect_image_files(directory)
        if not image_files:
            raise ValueError(f"No readable images found in directory: {directory}")

        first_image = self._load_image(image_files[0])
        height, width = first_image.shape[:2]
        return DataSourceInfo(height=height, width=width, frames=len(image_files), fps=None)

    def _from_file(self, file_path: Path) -> DataSourceInfo:
        if file_path.suffix.lower() == self._VIDEO_FILE_EXTENSION:
            return self._from_video(file_path)

        image = self._load_image(file_path)
        height, width = image.shape[:2]
        return DataSourceInfo(height=height, width=width, frames=1, fps=None)

    def _from_video(self, file_path: Path) -> DataSourceInfo:
        capture = cv2.VideoCapture(str(file_path))
        try:
            if not capture.isOpened():
                raise RuntimeError(f"Could not open video source: {file_path}")
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(capture.get(cv2.CAP_PROP_FPS))
        finally:
            capture.release()

        if width <= 0 or height <= 0:
            raise RuntimeError(f"Invalid video dimensions for: {file_path}")

        return DataSourceInfo(height=height, width=width, frames=frames, fps=fps)

    def _collect_image_files(self, directory: Path) -> list[Path]:
        files = [path for path in sorted(directory.iterdir()) if path.is_file()]
        return [path for path in files if cv2.haveImageReader(str(path))]

    def _load_image(self, file_path: Path):
        if not cv2.haveImageReader(str(file_path)):
            raise ValueError(f"Unsupported image format: {file_path}")

        image = cv2.imread(str(file_path))
        if image is None:
            raise RuntimeError(f"Could not read image from path: {file_path}")

        return image
