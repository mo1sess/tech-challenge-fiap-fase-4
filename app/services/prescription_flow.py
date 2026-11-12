from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, ClinicalEvent, Patient, Prescription, Severity
from app.schemas.clinical import PrescriptionCreate


DISCLAIMER = (
    "Regra educacional aplicada somente a prescricoes sinteticas. "
    "Nao representa validacao farmacologica ou recomendacao clinica."
)


def ingest_synthetic_prescription(
    db: Session,
    patient: Patient,
    payload: PrescriptionCreate,
) -> tuple[Prescription, list[ClinicalEvent], list[Alert]]:
    previous = db.scalar(
        select(Prescription)
        .where(
            Prescription.patient_id == patient.id,
            Prescription.medication_code == payload.medication_code,
        )
        .order_by(Prescription.recorded_at.desc())
        .limit(1)
    )
    prescription = Prescription(
        patient_id=patient.id,
        medication_code=payload.medication_code,
        action=payload.action,
        notes=payload.notes,
        recorded_at=payload.recorded_at or datetime.now(UTC),
        is_synthetic=True,
    )
    db.add(prescription)
    db.flush()

    active_actions = {"started", "changed"}
    anomaly: str | None = None
    if payload.action == "started" and previous and previous.action in active_actions:
        anomaly = "duplicate_start"
    elif payload.action in {"changed", "stopped"} and (
        previous is None or previous.action not in active_actions
    ):
        anomaly = "action_without_active_prescription"

    events: list[ClinicalEvent] = []
    alerts: list[Alert] = []
    if anomaly:
        event = ClinicalEvent(
            patient_id=patient.id,
            source="prescription_analysis",
            event_type="synthetic_prescription_sequence_anomaly",
            severity=Severity.MEDIUM.value,
            title="Sequencia demonstrativa de prescricao requer revisao",
            description=(
                "A ordem das acoes da prescricao sintetica nao corresponde "
                "ao estado anterior registrado."
            ),
            payload={
                "anomaly": anomaly,
                "prescription_id": prescription.id,
                "medication_code": prescription.medication_code,
                "current_action": prescription.action,
                "previous_action": previous.action if previous else None,
                "requires_human_review": True,
                "disclaimer": DISCLAIMER,
            },
            occurred_at=prescription.recorded_at,
        )
        db.add(event)
        db.flush()
        alert = Alert(
            event_id=event.id,
            patient_id=patient.id,
            severity=Severity.MEDIUM.value,
            message=f"Revisar sequencia sintetica de prescricao. {DISCLAIMER}",
        )
        db.add(alert)
        events.append(event)
        alerts.append(alert)

    db.commit()
    db.refresh(prescription)
    for item in [*events, *alerts]:
        db.refresh(item)
    return prescription, events, alerts
