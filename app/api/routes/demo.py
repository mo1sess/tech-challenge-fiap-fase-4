from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Patient
from app.schemas.clinical import DemoFlowResponse, MeasurementCreate, MeasurementIngestResponse
from app.services.clinical_flow import ingest_synthetic_measurement
from app.services.vital_signs import DISCLAIMER


router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/vital-alert", response_model=DemoFlowResponse)
def run_vital_alert_demo(db: Session = Depends(get_db)) -> DemoFlowResponse:
    patient = db.scalar(select(Patient).where(Patient.code == "MG-DEMO-001"))
    if patient is None:
        patient = Patient(
            code="MG-DEMO-001",
            alias="Paciente Sintetico Alfa",
            birth_year=1985,
            notes="Registro criado automaticamente para demonstracao.",
            is_synthetic=True,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    payload = MeasurementCreate(
        heart_rate_bpm=148,
        spo2_percent=84,
        systolic_mmhg=78,
        diastolic_mmhg=48,
        source="demo_button",
    )
    measurement, events, alerts = ingest_synthetic_measurement(db, patient, payload)
    return DemoFlowResponse(
        patient=patient,
        result=MeasurementIngestResponse(
            measurement=measurement,
            events=events,
            alerts=alerts,
            disclaimer=DISCLAIMER,
        ),
    )

