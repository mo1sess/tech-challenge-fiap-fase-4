from datetime import datetime

from app.schemas.common import ORMModel


class MediaFileRead(ORMModel):
    id: str
    patient_id: str
    kind: str
    original_filename: str
    content_type: str
    sha256: str
    size_bytes: int
    is_synthetic: bool
    created_at: datetime


class ProcessingJobRead(ORMModel):
    id: str
    patient_id: str
    media_file_id: str | None
    job_type: str
    status: str
    progress: float
    result: dict
    error: str | None
    created_at: datetime
    updated_at: datetime


class MediaUploadResponse(ORMModel):
    media: MediaFileRead
    job: ProcessingJobRead
    note: str

