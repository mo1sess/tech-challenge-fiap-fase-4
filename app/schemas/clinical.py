from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.patient import PatientRead


class MeasurementCreate(BaseModel):
    measured_at: datetime | None = None
    heart_rate_bpm: float | None = Field(default=None, ge=0, le=300)
    spo2_percent: float | None = Field(default=None, ge=0, le=100)
    systolic_mmhg: float | None = Field(default=None, ge=0, le=350)
    diastolic_mmhg: float | None = Field(default=None, ge=0, le=250)
    source: str = Field(default="synthetic_simulator", max_length=80)
    is_synthetic: Literal[True] = True


class MeasurementRead(ORMModel):
    id: str
    patient_id: str
    measured_at: datetime
    heart_rate_bpm: float | None
    spo2_percent: float | None
    systolic_mmhg: float | None
    diastolic_mmhg: float | None
    source: str
    is_synthetic: bool
    created_at: datetime


class EventRead(ORMModel):
    id: str
    patient_id: str
    measurement_id: str | None
    source: str
    event_type: str
    severity: str
    title: str
    description: str
    payload: dict
    occurred_at: datetime
    created_at: datetime


class AlertRead(ORMModel):
    id: str
    event_id: str
    patient_id: str
    severity: str
    status: str
    message: str
    created_at: datetime
    acknowledged_at: datetime | None


class MeasurementIngestResponse(BaseModel):
    measurement: MeasurementRead
    events: list[EventRead]
    alerts: list[AlertRead]
    disclaimer: str


class AlertStatusUpdate(BaseModel):
    status: Literal["acknowledged", "resolved"]


class DemoFlowResponse(BaseModel):
    patient: PatientRead
    result: MeasurementIngestResponse


class PrescriptionCreate(BaseModel):
    medication_code: str = Field(min_length=2, max_length=80)
    action: Literal["started", "changed", "stopped"]
    notes: str | None = Field(default=None, max_length=1000)
    recorded_at: datetime | None = None
    is_synthetic: Literal[True] = True


class PrescriptionRead(ORMModel):
    id: str
    patient_id: str
    medication_code: str
    action: str
    notes: str | None
    recorded_at: datetime
    is_synthetic: bool

