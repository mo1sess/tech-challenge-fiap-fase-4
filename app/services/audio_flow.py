
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import (Alert, ClinicalEvent, JobStatus, MediaFile, Patient,
                           ProcessingJob)
from app.modules.audio.acoustic import AcousticAnalysisError, analyze_acoustics
from app.modules.audio.azure_speech import (AudioTranscriptionError,
                                            transcribe_wav)
from app.modules.audio.text_analysis import analyze_text
from app.services.audio_event_flow import create_audio_review_events

AUDIO_DISCLAIMER = (
    "Resultado educacional de analise de audio sintetico. "
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
        raise ValueError(
            "O job informado nao e de analise de audio."
        )

    if not media.is_synthetic or not patient.is_synthetic:
        raise ValueError(
            "Somente dados sinteticos sao permitidos."
        )

    job.status = JobStatus.PROCESSING.value
    job.progress = 10.0
    job.error = None
    db.commit()

    try:
        audio_path = Path(media.storage_path)

        # 1. Transcricao com Azure Speech
        transcription = transcribe_wav(
            audio_path,
            settings,
        )

        # 2. Analise acustica local
        acoustic = analyze_acoustics(audio_path)

        # 3. Analise textual contextual
        text_analysis = analyze_text(
            str(transcription.get("text", ""))
        )

        # 4. Geracao de eventos demonstrativos
        events = create_audio_review_events(
            db,
            patient_id=patient.id,
            job_id=job.id,
            media_file_id=media.id,
            text_analysis=text_analysis.to_dict(),
        )

        # Alertas clinicos automaticos ainda nao implementados
        alerts: list[Alert] = []

        # 5. Persistencia do resultado
        job.status = JobStatus.COMPLETED.value
        job.progress = 100.0
        job.result = {
            "analysis": {
                "transcription": transcription,
                "acoustic": acoustic.to_dict(),
                "text_analysis": text_analysis.to_dict(),
                "disclaimer": AUDIO_DISCLAIMER,
            },
            "event_ids": [event.id for event in events],
            "alert_ids": [],
        }

        db.commit()
        db.refresh(job)

        for event in events:
            db.refresh(event)

        return job, events, alerts

    except (
        AudioTranscriptionError,
        AcousticAnalysisError,
        OSError,
        ValueError,
    ) as exc:
        db.rollback()

        persisted_job = db.get(ProcessingJob, job.id)

        if persisted_job is not None:
            persisted_job.status = JobStatus.FAILED.value
            persisted_job.progress = 100.0
            persisted_job.error = str(exc)
            db.commit()

        raise
