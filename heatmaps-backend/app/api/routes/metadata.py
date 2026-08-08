from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas import DefaultsResponse
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/defaults")
async def defaults() -> JSONResponse:
    fixed_max, alpha, sigma = get_settings().get_visualizer_defaults()

    return JSONResponse(
        status_code=200,
        content=DefaultsResponse(
            fixed_max=fixed_max,
            alpha=alpha,
            sigma=sigma,
        ).model_dump(),
    )
