
from datetime import UTC, datetime
from itertools import product

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ClinicalEvent, Patient, Severity

SOURCE = "multimodal_correlation"
EVENT_TYPE = "synthetic_multimodal_correlation_v2"
RULE_VERSION = "multimodal_temporal_v2"

EVENT_TYPES = {
    "audio_analysis": {
        "audio_help_request_review",
        "audio_pain_report_review",
        "audio_breathing_report_review",
    },
    "video_analysis": {
        "sustained_low_motion",
        "abrupt_visual_change",
    },
    "vital_signs": {
        "synthetic_vital_sign_anomaly",
    },
}

SOURCE_NAMES = {
    "audio_analysis": "audio",
    "video_analysis": "video",
    "vital_signs": "vital",
}


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def event_key(events: tuple[ClinicalEvent, ...]) -> tuple[str, ...]:
    return tuple(sorted(event.id for event in events))


def within_window(
    events: tuple[ClinicalEvent, ...],
    window_minutes: int,
) -> bool:
    timestamps = [as_utc(e.occurred_at) for e in events]
    span_seconds = (
        max(timestamps) - min(timestamps)
    ).total_seconds()
    return span_seconds <= window_minutes * 60


def load_events(
    db: Session,
    patient_id: str,
    source: str,
) -> list[ClinicalEvent]:
    return list(
        db.scalars(
            select(ClinicalEvent)
            .where(
                ClinicalEvent.patient_id == patient_id,
                ClinicalEvent.source == source,
                ClinicalEvent.event_type.in_(EVENT_TYPES[source]),
            )
            .order_by(ClinicalEvent.occurred_at.desc())
            .limit(30)
        )
    )


def correlate_multimodal_v2(
    db: Session,
    *,
    patient_id: str,
    window_minutes: int = 5,
) -> list[ClinicalEvent]:

    patient = db.get(Patient, patient_id)
    if patient is None:
        raise ValueError("Patient not found")
    if not patient.is_synthetic:
        raise ValueError("Only synthetic patients are supported")
    if not 1 <= window_minutes <= 60:
        raise ValueError("window_minutes must be between 1 and 60")

    audio = load_events(db, patient_id, "audio_analysis")
    video = load_events(db, patient_id, "video_analysis")
    vital = load_events(db, patient_id, "vital_signs")

    candidates: dict[tuple[str, ...], tuple[ClinicalEvent, ...]] = {}

    # Three-source correlations take priority.
    for group in product(audio, video, vital):
        if within_window(group, window_minutes):
            candidates[event_key(group)] = group

    triple_keys = [
        set(key) for key in candidates
    ]

    # Add pairs involving video when they are not
    # already represented by an eligible triple.
    for left, right in ((audio, video), (video, vital)):
        for group in product(left, right):
            if not within_window(group, window_minutes):
                continue

            key = event_key(group)

            if any(
                set(key).issubset(triple)
                for triple in triple_keys
            ):
                continue

            candidates[key] = group

    previous = list(
        db.scalars(
            select(ClinicalEvent)
            .where(
                ClinicalEvent.patient_id == patient_id,
                ClinicalEvent.source == SOURCE,
                ClinicalEvent.event_type == EVENT_TYPE,
            )
        )
    )

    existing_keys = {
        tuple(sorted(event.payload.get("source_event_ids", [])))
        for event in previous
    }

    created = []

    for key, group in candidates.items():
        if key in existing_keys:
            continue

        ordered = tuple(
            sorted(group, key=lambda e: as_utc(e.occurred_at))
        )
        timestamps = [as_utc(e.occurred_at) for e in ordered]

        span_seconds = (
            max(timestamps) - min(timestamps)
        ).total_seconds()

        sources = sorted(
            SOURCE_NAMES[event.source] for event in ordered
        )

        correlation = ClinicalEvent(
            patient_id=patient_id,
            source=SOURCE,
            event_type=EVENT_TYPE,
            severity=Severity.LOW.value,
            title="Correlação multimodal sintética",
            description=(
                "Eventos de diferentes fontes foram identificados "
                "para o mesmo paciente dentro de uma janela temporal. "
                "Não implica causalidade ou diagnóstico."
            ),
            occurred_at=max(timestamps),
            payload={
                "rule_version": RULE_VERSION,
                "source_event_ids": list(key),
                "sources": sources,
                "source_events": [
                    {
                        "event_id": event.id,
                        "source": event.source,
                        "event_type": event.event_type,
                        "severity": event.severity,
                        "occurred_at": as_utc(
                            event.occurred_at
                        ).isoformat(),
                    }
                    for event in ordered
                ],
                "source_count": len(group),
                "time_span_seconds": round(span_seconds, 3),
                "window_minutes": window_minutes,
                "correlation_type": "temporal_cooccurrence",
                "requires_human_review": True,
                "disclaimer": (
                    "Correlacao educacional de dados sinteticos. "
                    "Nao representa diagnostico ou risco clinico."
                ),
            },
        )

        db.add(correlation)
        db.flush()

        created.append(correlation)
        existing_keys.add(key)

    db.commit()

    for event in created:
        db.refresh(event)

    return created
