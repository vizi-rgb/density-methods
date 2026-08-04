from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorDetail, ErrorResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())
