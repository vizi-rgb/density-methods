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
    staging_video_path,
    video_url,
)
from app.services.video_normalizer import VideoNormalizeError, normalize_to_mp4

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
    staging_path = staging_video_path(settings, video_id, f".{kind.extension}")
    # Always normalized to MP4/H.264 below, regardless of the uploaded
    # container/codec — see normalize_to_mp4 for why.
    path = finalize_video_path(settings, video_id, ".mp4")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    total_bytes = len(first_chunk)

    try:
        with staging_path.open("wb") as out:
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

        try:
            await normalize_to_mp4(staging_path, path)
        except VideoNormalizeError as exc:
            raise ApiError(
                422,
                "video_processing_failed",
                "Uploaded file could not be processed as a video.",
            ) from exc
    except ApiError:
        path.unlink(missing_ok=True)
        raise
    finally:
        staging_path.unlink(missing_ok=True)

    return VideoUploadResponse(
        video_id=video_id,
        video_url=video_url(str(request.base_url), video_id, path),
    )
