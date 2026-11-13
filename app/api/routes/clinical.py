from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import (
    Alert,
    AlertStatus,
    ClinicalEvent,
    ClinicalMeasurement,
    Patient,
    PatientMovement,
    Prescription,
)
from app.schemas.clinical import (
    AlertRead,
    AlertStatusUpdate,
    EventRead,
    MeasurementCreate,
    MeasurementIngestResponse,
    MeasurementRead,
    MovementCreate,
    MovementIngestResponse,
    MovementRead,
    PrescriptionCreate,
    PrescriptionIngestResponse,
    PrescriptionRead,
)
from app.services.clinical_flow import ingest_synthetic_measurement
from app.services.movement_flow import DISCLAIMER as MOVEMENT_DISCLAIMER
from app.services.movement_flow import ingest_synthetic_movement
from app.services.prescription_flow import DISCLAIMER as PRESCRIPTION_DISCLAIMER
from app.services.prescription_flow import ingest_synthetic_prescription
from app.services.vital_signs import DISCLAIMER


router = APIRouter(tags=["clinical"])


def require_patient(db: Session, patient_id: str) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("/patients/{patient_id}/measurements", response_model=MeasurementIngestResponse, status_code=201)
def create_measurement(
    patient_id: str,
    payload: MeasurementCreate,
    db: Session = Depends(get_db),
) -> MeasurementIngestResponse:
    patient = require_patient(db, patient_id)
    measurement, events, alerts = ingest_synthetic_measurement(db, patient, payload)
    return MeasurementIngestResponse(
        measurement=measurement,
        events=events,
        alerts=alerts,
        disclaimer=DISCLAIMER,
    )


@router.get("/patients/{patient_id}/measurements", response_model=list[MeasurementRead])
def list_measurements(
    patient_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ClinicalMeasurement]:
    require_patient(db, patient_id)
    statement = (
        select(ClinicalMeasurement)
        .where(ClinicalMeasurement.patient_id == patient_id)
        .order_by(ClinicalMeasurement.measured_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.post("/patients/{patient_id}/prescriptions", response_model=PrescriptionRead, status_code=201)
def create_prescription(
    patient_id: str,
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
) -> Prescription:
    require_patient(db, patient_id)
    prescription = Prescription(
        patient_id=patient_id,
        medication_code=payload.medication_code,
        action=payload.action,
        notes=payload.notes,
        recorded_at=payload.recorded_at or datetime.now(UTC),
        is_synthetic=True,
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription


@router.get("/patients/{patient_id}/prescriptions", response_model=list[PrescriptionRead])
def list_prescriptions(patient_id: str, db: Session = Depends(get_db)) -> list[Prescription]:
    require_patient(db, patient_id)
    statement = select(Prescription).where(Prescription.patient_id == patient_id).order_by(Prescription.recorded_at.desc())
    return list(db.scalars(statement))


@router.post(
    "/patients/{patient_id}/prescriptions/evaluate",
    response_model=PrescriptionIngestResponse,
    status_code=201,
)
def evaluate_prescription(
    patient_id: str,
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
) -> PrescriptionIngestResponse:
    patient = require_patient(db, patient_id)
    prescription, events, alerts = ingest_synthetic_prescription(db, patient, payload)
    return PrescriptionIngestResponse(
        prescription=prescription,
        events=events,
        alerts=alerts,
        disclaimer=PRESCRIPTION_DISCLAIMER,
    )


@router.post(
    "/patients/{patient_id}/movements",
    response_model=MovementIngestResponse,
    status_code=201,
)
def create_movement(
    patient_id: str,
    payload: MovementCreate,
    db: Session = Depends(get_db),
) -> MovementIngestResponse:
    patient = require_patient(db, patient_id)
    movement, events, alerts = ingest_synthetic_movement(db, patient, payload)
    return MovementIngestResponse(
        movement=movement,
        events=events,
        alerts=alerts,
        disclaimer=MOVEMENT_DISCLAIMER,
    )


@router.get(
    "/patients/{patient_id}/movements",
    response_model=list[MovementRead],
)
def list_movements(
    patient_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[PatientMovement]:
    require_patient(db, patient_id)
    statement = (
        select(PatientMovement)
        .where(PatientMovement.patient_id == patient_id)
        .order_by(PatientMovement.recorded_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.get("/events", response_model=list[EventRead])
def list_events(
    patient_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ClinicalEvent]:
    statement = select(ClinicalEvent)
    if patient_id:
        statement = statement.where(ClinicalEvent.patient_id == patient_id)
    return list(db.scalars(statement.order_by(ClinicalEvent.occurred_at.desc()).limit(limit)))


@router.get("/alerts", response_model=list[AlertRead])
def list_alerts(
    patient_id: str | None = None,
    alert_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Alert]:
    statement = select(Alert)
    if patient_id:
        statement = statement.where(Alert.patient_id == patient_id)
    if alert_status:
        statement = statement.where(Alert.status == alert_status)
    return list(db.scalars(statement.order_by(Alert.created_at.desc()).limit(limit)))


@router.patch("/alerts/{alert_id}", response_model=AlertRead)
def update_alert(alert_id: str, payload: AlertStatusUpdate, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = payload.status
    if payload.status == AlertStatus.ACKNOWLEDGED.value:
        alert.acknowledged_at = datetime.now(UTC)
    db.commit()
    db.refresh(alert)
    return alert

