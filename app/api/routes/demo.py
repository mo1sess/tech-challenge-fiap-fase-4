import hashlib
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import MediaFile, Patient, ProcessingJob
from app.modules.video.processor import DISCLAIMER as VIDEO_DISCLAIMER
from app.modules.video.processor import create_synthetic_low_motion_video
from app.schemas.clinical import DemoFlowResponse, MeasurementCreate, MeasurementIngestResponse
from app.schemas.media import VideoDemoResponse, VideoJobProcessResponse
from app.services.clinical_flow import ingest_synthetic_measurement
from app.services.video_flow import process_video_job
from app.services.vital_signs import DISCLAIMER


router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/vital-alert", response_model=DemoFlowResponse)
def run_vital_alert_demo(db: Session = Depends(get_db)) -> DemoFlowResponse:
    patient = db.scalar(select(Patient).where(Patient.code == "MG-DEMO-001"))
    if patient is None:
        patient = Patient(
            code="MG-DEMO-001",
            alias="Paciente Sintetico Alfa",
            birth_year=1985,
            notes="Registro criado automaticamente para demonstracao.",
            is_synthetic=True,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    payload = MeasurementCreate(
        heart_rate_bpm=148,
        spo2_percent=84,
        systolic_mmhg=78,
        diastolic_mmhg=48,
        source="demo_button",
    )
    measurement, events, alerts = ingest_synthetic_measurement(db, patient, payload)
    return DemoFlowResponse(
        patient=patient,
        result=MeasurementIngestResponse(
            measurement=measurement,
            events=events,
            alerts=alerts,
            disclaimer=DISCLAIMER,
        ),
    )


@router.post("/video-alert", response_model=VideoDemoResponse)
def run_video_alert_demo(request: Request, db: Session = Depends(get_db)) -> VideoDemoResponse:
    patient = db.scalar(select(Patient).where(Patient.code == "MG-VIDEO-DEMO-001"))
    if patient is None:
        patient = Patient(
            code="MG-VIDEO-DEMO-001",
            alias="Paciente Geometrico Sintetico",
            birth_year=1990,
            notes="Registro educacional associado a formas geometricas geradas por codigo.",
            is_synthetic=True,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    request.app.state.settings.storage_dir.mkdir(parents=True, exist_ok=True)
    destination = request.app.state.settings.storage_dir / f"video_demo_{uuid.uuid4().hex}.avi"
    create_synthetic_low_motion_video(destination)
    content = destination.read_bytes()
    media = MediaFile(
        patient_id=patient.id,
        kind="video",
        original_filename="movimento_geometrico_sintetico.avi",
        content_type="video/x-msvideo",
        storage_path=str(destination),
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        is_synthetic=True,
    )
    db.add(media)
    db.flush()
    job = ProcessingJob(
        patient_id=patient.id,
        media_file_id=media.id,
        job_type="video_analysis",
        status="queued",
        result={},
    )
    db.add(job)
    db.commit()
    db.refresh(media)
    db.refresh(job)

    processed_job, events, alerts = process_video_job(
        db,
        job,
        media,
        patient,
        request.app.state.settings,
    )
    return VideoDemoResponse(
        patient=patient,
        media=media,
        processing=VideoJobProcessResponse(
            job=processed_job,
            events=events,
            alerts=alerts,
            disclaimer=VIDEO_DISCLAIMER,
        ),
    )

