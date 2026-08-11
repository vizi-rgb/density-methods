"""Transcodes an uploaded video to a known-good H.264 MP4 via the system
ffmpeg binary before it's ever handed to OpenCV.

Why: opencv-python wheels bundle their own statically-linked ffmpeg, built
per-platform by opencv's release pipeline — codec support (AV1 in
particular) varies between those builds and is fixed at wheel-install time,
so it can't be fixed by installing packages in the container. The system
ffmpeg binary (apt-installed, see Dockerfile) has full codec support
(libdav1d/libaom) and is already used for output encoding in mp4_encoder.py.
Normalizing every upload to H.264 here means cv2 never has to decode
anything but the one codec we know it supports, regardless of what the
user uploaded.
"""

from __future__ import annotations

import asyncio
from pathlib import Path


class VideoNormalizeError(RuntimeError):
    pass


async def normalize_to_mp4(source_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source_path),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        output_path.unlink(missing_ok=True)
        tail = stderr.decode(errors="replace").strip() or "(no ffmpeg output captured)"
        raise VideoNormalizeError(f"ffmpeg exited with code {process.returncode}: {tail}")
