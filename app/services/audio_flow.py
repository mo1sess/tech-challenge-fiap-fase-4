
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import (Alert, ClinicalEvent, JobStatus, MediaFile, Patient,
                           ProcessingJob)
from app.modules.audio.azure_speech import (AudioTranscriptionError,
                                            transcribe_wav)

AUDIO_DISCLAIMER = (
    "Resultado educacional de transcricao de audio sintetico. "
    "Nao constitui diagnostico ou recomendacao clinica."
)


def process_audio_job(
    db: Session,
    job: ProcessingJob,
    media: MediaFile,
    patient: Patient,
    settings: Settings,
) -> tuple[ProcessingJob, list[ClinicalEvent], list[Alert]]:
    if media.kind != "audio" or job.job_type != "audio_analysis":
        raise ValueError("O job informado nao e de analise de audio.")

    if not media.is_synthetic or not patient.is_synthetic:
        raise ValueError("Somente dados sinteticos sao permitidos.")

    job.status = JobStatus.PROCESSING.value
    job.progress = 10.0
    job.error = None
    db.commit()

    try:
        transcription = transcribe_wav(
            Path(media.storage_path),
            settings,
        )

        job.status = JobStatus.COMPLETED.value
        job.progress = 100.0
        job.result = {
            "analysis": {
                "transcription": transcription,
                "disclaimer": AUDIO_DISCLAIMER,
            },
            "event_ids": [],
            "alert_ids": [],
        }

        db.commit()
        db.refresh(job)

        return job, [], []

    except (AudioTranscriptionError, OSError, ValueError) as exc:
        db.rollback()

        persisted_job = db.get(ProcessingJob, job.id)
        if persisted_job is not None:
            persisted_job.status = JobStatus.FAILED.value
            persisted_job.progress = 100.0
            persisted_job.error = str(exc)
            db.commit()

        raise
