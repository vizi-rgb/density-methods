from __future__ import annotations

import filetype
from fastapi import APIRouter, File, Request, UploadFile

from app.api.errors import ApiError
from app.api.schemas import VideoUploadResponse
from app.config import get_settings
from app.services.storage import (
    ensure_base_dirs,
    finalize_video_path,
    new_id,
    video_url,
)

router = APIRouter()

_CHUNK_SIZE = 1024 * 1024


@router.post("/api/videos", response_model=VideoUploadResponse, status_code=202)
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
) -> VideoUploadResponse:
    settings = get_settings()
    ensure_base_dirs(settings)

    first_chunk = await file.read(_CHUNK_SIZE)
    if not first_chunk:
        raise ApiError(400, "empty_file", "Uploaded file is empty.")

    kind = filetype.guess(first_chunk)
    if kind is None or not kind.mime.startswith("video/"):
        raise ApiError(
            415,
            "unsupported_media_type",
            "Uploaded file is not a supported video format.",
        )

    video_id = new_id()
    suffix = f".{kind.extension}"
    path = finalize_video_path(settings, video_id, suffix)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    total_bytes = len(first_chunk)

    try:
        with path.open("wb") as out:
            out.write(first_chunk)
            while chunk := await file.read(_CHUNK_SIZE):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise ApiError(
                        413,
                        "file_too_large",
                        f"File exceeds the {settings.max_upload_mb}MB limit.",
                    )
                out.write(chunk)
    except ApiError:
        path.unlink(missing_ok=True)
        raise

    return VideoUploadResponse(
        video_id=video_id,
        video_url=video_url(str(request.base_url), video_id, path),
    )
