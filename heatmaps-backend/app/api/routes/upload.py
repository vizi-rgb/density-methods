from __future__ import annotations

import filetype
from fastapi import APIRouter, File, Form, Request, UploadFile

from app.api.errors import ApiError
from app.api.schemas import UploadResponse
from app.config import HEATMAP_TYPES, get_settings
from app.services.storage import ensure_base_dirs, new_job_id, upload_path
from app.worker import queue as worker_queue

router = APIRouter()

_CHUNK_SIZE = 1024 * 1024


@router.post("/api/upload", response_model=UploadResponse, status_code=202)
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    heatmap_types: list[str] = Form(...),
) -> UploadResponse:
    settings = get_settings()
    ensure_base_dirs(settings)

    selected_types = _validate_heatmap_types(heatmap_types)

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

    job_id = new_job_id()
    destination = upload_path(settings, job_id, f".{kind.extension}")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    total_bytes = len(first_chunk)

    try:
        with destination.open("wb") as out:
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
        destination.unlink(missing_ok=True)
        raise

    worker_queue.get_queue().enqueue(
        "app.worker.tasks.process_video",
        job_id,
        selected_types,
        str(destination),
        str(request.base_url),
        job_id=job_id,
        meta={"progress": 0},
        result_ttl=settings.job_ttl_seconds,
        failure_ttl=settings.job_ttl_seconds,
    )

    return UploadResponse(job_id=job_id)


def _validate_heatmap_types(raw_types: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_type in raw_types:
        if raw_type not in HEATMAP_TYPES:
            raise ApiError(
                422,
                "invalid_heatmap_types",
                f"Unsupported heatmap type: {raw_type!r}. Allowed: {sorted(HEATMAP_TYPES)}.",
            )
        if raw_type not in seen:
            seen.add(raw_type)
            normalized.append(raw_type)

    if not normalized:
        raise ApiError(
            422,
            "invalid_heatmap_types",
            "At least one heatmap_types value is required.",
        )
    return normalized
