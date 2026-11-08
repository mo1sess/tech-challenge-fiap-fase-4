from sqlalchemy.orm import Session

from app.db.models import Alert, ClinicalEvent, ClinicalMeasurement, Patient, utcnow
from app.schemas.clinical import MeasurementCreate
from app.services.vital_signs import DISCLAIMER, evaluate_vital_signs, highest_severity


def ingest_synthetic_measurement(
    db: Session,
    patient: Patient,
    payload: MeasurementCreate,
) -> tuple[ClinicalMeasurement, list[ClinicalEvent], list[Alert]]:
    measurement = ClinicalMeasurement(
        patient_id=patient.id,
        measured_at=payload.measured_at or utcnow(),
        heart_rate_bpm=payload.heart_rate_bpm,
        spo2_percent=payload.spo2_percent,
        systolic_mmhg=payload.systolic_mmhg,
        diastolic_mmhg=payload.diastolic_mmhg,
        source=payload.source,
        is_synthetic=True,
    )
    db.add(measurement)
    db.flush()

    detections = evaluate_vital_signs(measurement)
    events: list[ClinicalEvent] = []
    alerts: list[Alert] = []

    if detections:
        severity = highest_severity(detections)
        details = [
            {
                "metric": item.metric,
                "value": item.value,
                "severity": item.severity.value,
                "reason": item.reason,
            }
            for item in detections
        ]
        event = ClinicalEvent(
            patient_id=patient.id,
            measurement_id=measurement.id,
            source="vital_signs",
            event_type="synthetic_vital_sign_anomaly",
            severity=severity.value,
            title="Anomalia demonstrativa em sinais vitais",
            description=f"Foram identificadas {len(detections)} condicoes fora das faixas educacionais configuradas.",
            payload={"detections": details, "disclaimer": DISCLAIMER},
            occurred_at=measurement.measured_at,
        )
        db.add(event)
        db.flush()

        alert = Alert(
            event_id=event.id,
            patient_id=patient.id,
            severity=severity.value,
            message=f"Revisar evento sintetico de sinais vitais ({severity.value}). {DISCLAIMER}",
        )
        db.add(alert)
        events.append(event)
        alerts.append(alert)

    db.commit()
    db.refresh(measurement)
    for item in [*events, *alerts]:
        db.refresh(item)
    return measurement, events, alerts

