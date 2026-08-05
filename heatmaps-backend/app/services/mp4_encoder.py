"""ffmpeg subprocess: raw BGR frames in, a single playable MP4 out.

Avoids writing per-frame images to disk — frames are piped straight into
ffmpeg as they're produced by the pipeline. `-movflags +faststart` moves the
moov atom to the front of the file so the frontend's <video> tag can seek
without downloading the whole file first.
"""

from __future__ import annotations

import subprocess
import threading
from collections import deque
from pathlib import Path

import numpy as np


class Mp4EncoderError(RuntimeError):
    pass


class Mp4Encoder:
    def __init__(self, output_path: Path, width: int, height: int, fps: int) -> None:
        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        # Drain stderr continuously in the background: ffmpeg logs steadily
        # while we stream raw frames into stdin, and if stderr's pipe buffer
        # fills up unread, ffmpeg blocks on writing it, which deadlocks our
        # stdin writes.
        self._stderr_tail: deque[str] = deque(maxlen=200)
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def _drain_stderr(self) -> None:
        assert self._process.stderr is not None
        for line in self._process.stderr:
            self._stderr_tail.append(line.decode(errors="replace").rstrip())

    def write_frame(self, frame: np.ndarray) -> None:
        assert self._process.stdin is not None
        try:
            self._process.stdin.write(frame.tobytes())
        except BrokenPipeError as exc:
            raise Mp4EncoderError(
                f"ffmpeg process exited early: {self._tail_message()}"
            ) from exc

    def close(self) -> None:
        if self._process.stdin is not None:
            try:
                self._process.stdin.close()
            except BrokenPipeError:
                pass
        return_code = self._process.wait()
        self._stderr_thread.join(timeout=5)
        if return_code != 0:
            raise Mp4EncoderError(
                f"ffmpeg exited with code {return_code}: {self._tail_message()}"
            )

    def kill(self) -> None:
        self._process.kill()
        self._process.wait()

    def _tail_message(self) -> str:
        return "\n".join(self._stderr_tail) or "(no ffmpeg output captured)"
