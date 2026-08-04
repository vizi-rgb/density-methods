from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class UploadResponse(BaseModel):
    job_id: str


class HealthResponse(BaseModel):
    status: str
    workers_online: int
    queued_jobs: int
