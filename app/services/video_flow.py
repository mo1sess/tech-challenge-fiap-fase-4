from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Alert, ClinicalEvent, JobStatus, MediaFile, Patient, ProcessingJob
from app.modules.video.processor import DISCLAIMER, VideoProcessingError, analyze_video


def process_video_job(
    db: Session,
    job: ProcessingJob,
    media: MediaFile,
    patient: Patient,
    settings: Settings,
) -> tuple[ProcessingJob, list[ClinicalEvent], list[Alert]]:
    if media.kind != "video" or job.job_type != "video_analysis":
        raise ValueError("Only video analysis jobs can be processed by this service")
    if not media.is_synthetic or not patient.is_synthetic:
        raise ValueError("Only synthetic video and patients are accepted")

    job.status = JobStatus.PROCESSING.value
    job.progress = 10.0
    job.error = None
    db.commit()

    try:
        analysis = analyze_video(
            Path(media.storage_path),
            sample_every_n_frames=settings.video_sample_every_n_frames,
            low_motion_threshold=settings.video_low_motion_threshold,
            abrupt_motion_threshold=settings.video_abrupt_motion_threshold,
            max_frames=settings.video_max_frames,
        )
        events: list[ClinicalEvent] = []
        alerts: list[Alert] = []
        for anomaly in analysis.anomalies:
            event = ClinicalEvent(
                patient_id=patient.id,
                source="video_analysis",
                event_type=anomaly["code"],
                severity=anomaly["severity"],
                title=anomaly["title"],
                description=anomaly["description"],
                payload={
                    "job_id": job.id,
                    "media_file_id": media.id,
                    "observed_value": anomaly["observed_value"],
                    "threshold": anomaly["threshold"],
                    "unit": anomaly["unit"],
                    "disclaimer": DISCLAIMER,
                },
            )
            db.add(event)
            db.flush()
            alert = Alert(
                event_id=event.id,
                patient_id=patient.id,
                severity=event.severity,
                message=f"Revisar evento demonstrativo de video: {event.title}. {DISCLAIMER}",
            )
            db.add(alert)
            events.append(event)
            alerts.append(alert)

        job.status = JobStatus.COMPLETED.value
        job.progress = 100.0
        job.result = {
            "analysis": analysis.to_dict(),
            "event_ids": [item.id for item in events],
            "alert_ids": [item.id for item in alerts],
        }
        db.commit()
        db.refresh(job)
        for item in [*events, *alerts]:
            db.refresh(item)
        return job, events, alerts
    except (VideoProcessingError, OSError, ValueError) as exc:
        db.rollback()
        persisted_job = db.get(ProcessingJob, job.id)
        if persisted_job is not None:
            persisted_job.status = JobStatus.FAILED.value
            persisted_job.error = str(exc)
            persisted_job.progress = 100.0
            db.commit()
        raise
