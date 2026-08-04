"""Per-heatmap-type ffmpeg subprocess: raw BGR frames in, VOD HLS out.

Avoids writing per-frame images or an intermediate MP4 to disk — frames are
piped straight into ffmpeg as they're produced by the pipeline.
"""

from __future__ import annotations

import subprocess
import threading
from collections import deque
from pathlib import Path

import numpy as np


class HlsEncoderError(RuntimeError):
    pass


class HlsEncoder:
    def __init__(
        self,
        output_dir: Path,
        width: int,
        height: int,
        fps: int,
        segment_seconds: int,
    ) -> None:
        gop = max(1, fps * segment_seconds)
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
            "-g",
            str(gop),
            "-keyint_min",
            str(gop),
            "-sc_threshold",
            "0",
            "-f",
            "hls",
            "-hls_time",
            str(segment_seconds),
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            str(output_dir / "segment_%03d.ts"),
            str(output_dir / "stream.m3u8"),
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
            raise HlsEncoderError(
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
            raise HlsEncoderError(
                f"ffmpeg exited with code {return_code}: {self._tail_message()}"
            )

    def kill(self) -> None:
        self._process.kill()
        self._process.wait()

    def _tail_message(self) -> str:
        return "\n".join(self._stderr_tail) or "(no ffmpeg output captured)"
