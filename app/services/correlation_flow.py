
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ClinicalEvent, Patient, Severity

CORRELATION_SOURCE = "multimodal_correlation"
CORRELATION_TYPE = "synthetic_audio_vital_correlation"
RULE_VERSION = "audio_vital_temporal_v1"

AUDIO_EVENT_TYPES = {
    "audio_help_request_review",
    "audio_pain_report_review",
    "audio_breathing_report_review",
}


def as_utc(value: datetime) -> datetime:
    """
    Normalize datetimes for comparison.

    SQLite may return naive timestamps; the application
    stores timestamps using UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def correlate_audio_and_vitals(
    db: Session,
    *,
    patient_id: str,
    window_minutes: int = 5,
) -> list[ClinicalEvent]:
    """
    Correlate existing synthetic audio and vital-sign events.

    Correlation is based only on patient identity and
    temporal proximity, not clinical causality.

    Returns newly created correlation events.
    """

    patient = db.get(Patient, patient_id)

    if patient is None:
        raise ValueError("Patient not found")

    if not patient.is_synthetic:
        raise ValueError("Only synthetic patients are supported")

    if not 1 <= window_minutes <= 60:
        raise ValueError("window_minutes must be between 1 and 60")

    audio_events = list(
        db.scalars(
            select(ClinicalEvent)
            .where(
                ClinicalEvent.patient_id == patient_id,
                ClinicalEvent.source == "audio_analysis",
                ClinicalEvent.event_type.in_(AUDIO_EVENT_TYPES),
            )
            .order_by(ClinicalEvent.occurred_at.desc())
            .limit(100)
        )
    )

    vital_events = list(
        db.scalars(
            select(ClinicalEvent)
            .where(
                ClinicalEvent.patient_id == patient_id,
                ClinicalEvent.source == "vital_signs",
                ClinicalEvent.event_type
                == "synthetic_vital_sign_anomaly",
            )
            .order_by(ClinicalEvent.occurred_at.desc())
            .limit(100)
        )
    )

    previous_correlations = list(
        db.scalars(
            select(ClinicalEvent)
            .where(
                ClinicalEvent.patient_id == patient_id,
                ClinicalEvent.source == CORRELATION_SOURCE,
                ClinicalEvent.event_type == CORRELATION_TYPE,
            )
        )
    )

    existing_pairs = {
        (
            event.payload.get("audio_event_id"),
            event.payload.get("vital_event_id"),
        )
        for event in previous_correlations
    }

    created_events = []

    for audio in audio_events:
        for vital in vital_events:
            pair = (audio.id, vital.id)

            if pair in existing_pairs:
                continue

            audio_time = as_utc(audio.occurred_at)
            vital_time = as_utc(vital.occurred_at)

            time_difference = abs(
                (audio_time - vital_time).total_seconds()
            )

            if time_difference > window_minutes * 60:
                continue

            correlation = ClinicalEvent(
                patient_id=patient_id,
                source=CORRELATION_SOURCE,
                event_type=CORRELATION_TYPE,
                severity=Severity.LOW.value,
                title=(
                    "Correlação demonstrativa entre áudio "
                    "e sinais vitais"
                ),
                description=(
                    "Eventos sintéticos de áudio e sinais vitais "
                    "foram identificados para o mesmo paciente "
                    "dentro da janela temporal configurada. "
                    "A correlação não representa diagnóstico "
                    "ou relação causal."
                ),
                occurred_at=max(audio_time, vital_time),
                payload={
                    "rule_version": RULE_VERSION,
                    "audio_event_id": audio.id,
                    "vital_event_id": vital.id,
                    "source_event_ids": [
                        audio.id,
                        vital.id,
                    ],
                    "source_types": [
                        audio.event_type,
                        vital.event_type,
                    ],
                    "audio_signal": audio.payload.get("signal"),
                    "audio_occurred_at": audio_time.isoformat(),
                    "vital_occurred_at": vital_time.isoformat(),
                    "time_difference_seconds": round(
                        time_difference, 3
                    ),
                    "window_minutes": window_minutes,
                    "requires_human_review": True,
                    "correlation_type": "temporal_cooccurrence",
                    "disclaimer": (
                        "Correlação educacional de dados "
                        "sintéticos. Não representa diagnóstico "
                        "ou avaliação de risco clínico."
                    ),
                },
            )

            db.add(correlation)
            db.flush()

            created_events.append(correlation)
            existing_pairs.add(pair)

    db.commit()

    for event in created_events:
        db.refresh(event)

    return created_events
