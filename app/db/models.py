from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def uuid_string() -> str:
    return str(uuid.uuid4())


class MediaKind(StrEnum):
    AUDIO = "audio"
    VIDEO = "video"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    alias: Mapped[str] = mapped_column(String(120))
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    storage_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    media_file_id: Mapped[str | None] = mapped_column(ForeignKey("media_files.id"), nullable=True)
    job_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), default=JobStatus.QUEUED.value, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ClinicalMeasurement(Base):
    __tablename__ = "clinical_measurements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    heart_rate_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    spo2_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    systolic_mmhg: Mapped[float | None] = mapped_column(Float, nullable=True)
    diastolic_mmhg: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="synthetic_simulator")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    medication_code: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PatientMovement(Base):
    __tablename__ = "patient_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    from_location: Mapped[str] = mapped_column(String(80))
    to_location: Mapped[str] = mapped_column(String(80))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ClinicalEvent(Base):
    __tablename__ = "clinical_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    measurement_id: Mapped[str | None] = mapped_column(ForeignKey("clinical_measurements.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    event_id: Mapped[str] = mapped_column(ForeignKey("clinical_events.id"), unique=True, index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(30), default=AlertStatus.OPEN.value, index=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

