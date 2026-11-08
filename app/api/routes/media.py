import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import MediaFile, MediaKind, Patient, ProcessingJob
from app.modules.audio.processor import describe_pipeline as describe_audio_pipeline
from app.modules.video.processor import describe_pipeline as describe_video_pipeline
from app.schemas.media import MediaFileRead, MediaUploadResponse, ProcessingJobRead


router = APIRouter(tags=["media and jobs"])

ALLOWED_EXTENSIONS = {
    MediaKind.AUDIO.value: {".wav", ".mp3", ".m4a", ".ogg"},
    MediaKind.VIDEO.value: {".mp4", ".mov", ".avi", ".mkv"},
}


def infer_kind(upload: UploadFile, requested_kind: str | None) -> str:
    if requested_kind:
        kind = requested_kind.lower()
    elif (upload.content_type or "").startswith("audio/"):
        kind = MediaKind.AUDIO.value
    elif (upload.content_type or "").startswith("video/"):
        kind = MediaKind.VIDEO.value
    else:
        extension = Path(upload.filename or "").suffix.lower()
        kind = next((name for name, extensions in ALLOWED_EXTENSIONS.items() if extension in extensions), "")

    if kind not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Media kind must be audio or video")
    extension = Path(upload.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS[kind]:
        raise HTTPException(status_code=415, detail=f"Unsupported {kind} file extension")
    return kind


@router.post("/patients/{patient_id}/media", response_model=MediaUploadResponse, status_code=201)
async def upload_media(
    patient_id: str,
    request: Request,
    file: UploadFile = File(...),
    kind: str | None = Form(default=None),
    is_synthetic: bool = Form(default=True),
    db: Session = Depends(get_db),
) -> MediaUploadResponse:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not is_synthetic:
        raise HTTPException(status_code=422, detail="Only synthetic or explicitly fictional media is accepted")

    resolved_kind = infer_kind(file, kind)
    settings = request.app.state.settings
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds the {settings.max_upload_mb} MB limit")

    extension = Path(file.filename or "media").suffix.lower()
    digest = hashlib.sha256(content).hexdigest()
    storage_dir = Path(settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    media = MediaFile(
        patient_id=patient.id,
        kind=resolved_kind,
        original_filename=Path(file.filename or f"media{extension}").name,
        content_type=file.content_type or "application/octet-stream",
        storage_path="pending",
        sha256=digest,
        size_bytes=len(content),
        is_synthetic=True,
    )
    db.add(media)
    db.flush()

    destination = storage_dir / f"{media.id}{extension}"
    destination.write_bytes(content)
    media.storage_path = str(destination)

    pipeline = describe_audio_pipeline(destination) if resolved_kind == "audio" else describe_video_pipeline(destination)
    job = ProcessingJob(
        patient_id=patient.id,
        media_file_id=media.id,
        job_type=f"{resolved_kind}_analysis",
        status="queued",
        progress=0.0,
        result={"pipeline": pipeline},
    )
    db.add(job)
    db.commit()
    db.refresh(media)
    db.refresh(job)
    return MediaUploadResponse(
        media=media,
        job=job,
        note="Arquivo sintetico registrado. O job permanece na fila ate a implementacao do processador da proxima etapa.",
    )


@router.get("/media", response_model=list[MediaFileRead])
def list_media(
    patient_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[MediaFile]:
    statement = select(MediaFile)
    if patient_id:
        statement = statement.where(MediaFile.patient_id == patient_id)
    return list(db.scalars(statement.order_by(MediaFile.created_at.desc()).limit(limit)))


@router.get("/jobs", response_model=list[ProcessingJobRead])
def list_jobs(
    patient_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ProcessingJob]:
    statement = select(ProcessingJob)
    if patient_id:
        statement = statement.where(ProcessingJob.patient_id == patient_id)
    return list(db.scalars(statement.order_by(ProcessingJob.created_at.desc()).limit(limit)))


@router.get("/jobs/{job_id}", response_model=ProcessingJobRead)
def get_job(job_id: str, db: Session = Depends(get_db)) -> ProcessingJob:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

