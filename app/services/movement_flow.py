from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, ClinicalEvent, Patient, PatientMovement, Severity
from app.schemas.clinical import MovementCreate


DISCLAIMER = (
    "Regra educacional aplicada somente a movimentacoes sinteticas. "
    "Nao representa rastreamento ou avaliacao clinica."
)


def ingest_synthetic_movement(
    db: Session,
    patient: Patient,
    payload: MovementCreate,
) -> tuple[PatientMovement, list[ClinicalEvent], list[Alert]]:
    previous = db.scalar(
        select(PatientMovement)
        .where(PatientMovement.patient_id == patient.id)
        .order_by(PatientMovement.recorded_at.desc())
        .limit(1)
    )
    movement = PatientMovement(
        patient_id=patient.id,
        from_location=payload.from_location.strip(),
        to_location=payload.to_location.strip(),
        recorded_at=payload.recorded_at or datetime.now(UTC),
        is_synthetic=True,
    )
    db.add(movement)
    db.flush()

    anomalies: list[dict[str, str]] = []
    if movement.from_location.casefold() == movement.to_location.casefold():
        anomalies.append(
            {"code": "same_origin_destination", "severity": Severity.MEDIUM.value}
        )
    if previous and previous.to_location.casefold() != movement.from_location.casefold():
        anomalies.append(
            {"code": "location_continuity_mismatch", "severity": Severity.HIGH.value}
        )
    if previous:
        current_time = movement.recorded_at
        previous_time = previous.recorded_at
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        if previous_time.tzinfo is None:
            previous_time = previous_time.replace(tzinfo=UTC)
        if 0 <= (current_time - previous_time).total_seconds() < 120:
            anomalies.append(
                {"code": "rapid_repeated_transfer", "severity": Severity.MEDIUM.value}
            )

    events: list[ClinicalEvent] = []
    alerts: list[Alert] = []
    if anomalies:
        severity = (
            Severity.HIGH
            if any(item["severity"] == Severity.HIGH.value for item in anomalies)
            else Severity.MEDIUM
        )
        event = ClinicalEvent(
            patient_id=patient.id,
            source="movement_analysis",
            event_type="synthetic_movement_sequence_anomaly",
            severity=severity.value,
            title="Movimentacao sintetica requer revisao",
            description="A sequencia de localizacoes ficticias violou regras demonstrativas.",
            payload={
                "movement_id": movement.id,
                "from_location": movement.from_location,
                "to_location": movement.to_location,
                "anomalies": anomalies,
                "previous_destination": previous.to_location if previous else None,
                "requires_human_review": True,
                "disclaimer": DISCLAIMER,
            },
            occurred_at=movement.recorded_at,
        )
        db.add(event)
        db.flush()
        alert = Alert(
            event_id=event.id,
            patient_id=patient.id,
            severity=severity.value,
            message=f"Revisar movimentacao sintetica. {DISCLAIMER}",
        )
        db.add(alert)
        events.append(event)
        alerts.append(alert)

    db.commit()
    db.refresh(movement)
    for item in [*events, *alerts]:
        db.refresh(item)
    return movement, events, alerts
