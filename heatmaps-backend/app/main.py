from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import ApiError, api_error_handler
from app.api.routes import health, heatmaps, videos
from app.api.schemas import ErrorDetail, ErrorResponse
from app.config import get_settings
from app.services.storage import MEDIA_MOUNT_PATH, ensure_base_dirs


async def _validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    message = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()
    )
    body = ErrorResponse(error=ErrorDetail(code="invalid_request", message=message))
    return JSONResponse(status_code=400, content=body.model_dump())


def create_app() -> FastAPI:
    settings = get_settings()
    ensure_base_dirs(settings)

    app = FastAPI(title="heatmaps-backend")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Starlette's add_exception_handler is typed to accept `Exception`-typed
    # handlers only; narrower per-exception-type handlers are the documented,
    # correct usage but don't satisfy that contravariant signature check.
    app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error_handler)  # type: ignore[arg-type]

    app.include_router(videos.router)
    app.include_router(heatmaps.router)
    app.include_router(health.router)

    app.mount(
        MEDIA_MOUNT_PATH,
        StaticFiles(directory=settings.data_dir, check_dir=False),
        name="media",
    )

    return app


app = create_app()
