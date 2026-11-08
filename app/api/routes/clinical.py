from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Alert, AlertStatus, ClinicalEvent, ClinicalMeasurement, Patient, Prescription
from app.schemas.clinical import (
    AlertRead,
    AlertStatusUpdate,
    EventRead,
    MeasurementCreate,
    MeasurementIngestResponse,
    MeasurementRead,
    PrescriptionCreate,
    PrescriptionRead,
)
from app.services.clinical_flow import ingest_synthetic_measurement
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

