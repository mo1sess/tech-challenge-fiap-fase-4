
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.db.models import ClinicalEvent, Patient
from app.services.correlation_v2 import correlate_multimodal_v2

START = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)

TYPES = {
    "audio_analysis": "audio_help_request_review",
    "video_analysis": "sustained_low_motion",
    "vital_signs": "synthetic_vital_sign_anomaly",
}


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


def test_database_rejects_duplicate_correlation_key(db):
    patient = make_patient(db)

    make_event(
        db,
        patient.id,
        "audio_analysis",
        seconds=0,
    )

    make_event(
        db,
        patient.id,
        "video_analysis",
        seconds=60,
    )

    created = correlate(db, patient.id)

    assert len(created) == 1
    assert created[0].correlation_key is not None

    duplicate = ClinicalEvent(
        patient_id=patient.id,
        correlation_key=created[0].correlation_key,
        source="multimodal_correlation",
        event_type="synthetic_multimodal_correlation_v2",
        severity="low",
        title="Duplicate correlation",
        description="Database uniqueness test",
        payload=created[0].payload,
        occurred_at=created[0].occurred_at,
    )

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(duplicate)
            db.flush()

    # The original record remains valid.
    assert correlate(db, patient.id) == []

def make_patient(db, code="MG-CORR-001"):
    patient = Patient(
        code=code,
        alias="Synthetic patient",
        is_synthetic=True,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def make_event(
    db,
    patient_id,
    source,
    *,
    seconds=0,
    job_id=None,
    severity="low",
):
    payload = {"job_id": job_id} if job_id else {}

    item = ClinicalEvent(
        patient_id=patient_id,
        source=source,
        event_type=TYPES[source],
        severity=severity,
        title="Synthetic test event",
        description="Temporal correlation test",
        payload=payload,
        occurred_at=START + timedelta(seconds=seconds),
    )

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def correlate(db, patient_id, window=5):
    return correlate_multimodal_v2(
        db,
        patient_id=patient_id,
        window_minutes=window,
    )


def test_exact_window_boundary(db):
    patient = make_patient(db)

    make_event(db, patient.id, "audio_analysis")
    make_event(db, patient.id, "video_analysis", seconds=300)

    result = correlate(db, patient.id)

    assert len(result) == 1
    assert result[0].payload["time_span_seconds"] == 300


def test_outside_window(db):
    patient = make_patient(db)

    make_event(db, patient.id, "audio_analysis")
    make_event(db, patient.id, "video_analysis", seconds=301)

    assert correlate(db, patient.id) == []


def test_patient_isolation(db):
    first = make_patient(db, "MG-CORR-A")
    second = make_patient(db, "MG-CORR-B")

    make_event(db, first.id, "audio_analysis")
    make_event(db, second.id, "video_analysis")

    assert correlate(db, first.id) == []
    assert correlate(db, second.id) == []


def test_triple_uses_full_time_span(db):
    patient = make_patient(db)

    make_event(db, patient.id, "audio_analysis", seconds=0)
    make_event(db, patient.id, "video_analysis", seconds=180)
    make_event(db, patient.id, "vital_signs", seconds=360)

    result = correlate(db, patient.id)

    # Each neighboring pair qualifies.
    assert len(result) == 2

    # But the complete six-minute span does not.
    assert all(
        item.payload["source_count"] == 2
        for item in result
    )


def test_three_sources_take_priority(db):
    patient = make_patient(db)

    audio = make_event(
        db, patient.id, "audio_analysis", seconds=0
    )
    video = make_event(
        db, patient.id, "video_analysis", seconds=60
    )
    vital = make_event(
        db, patient.id, "vital_signs", seconds=120
    )

    result = correlate(db, patient.id)

    assert len(result) == 1

    payload = result[0].payload

    assert payload["source_count"] == 3
    assert set(payload["source_event_ids"]) == {
        audio.id, video.id, vital.id
    }


def test_video_job_deduplication(db):
    patient = make_patient(db)

    make_event(db, patient.id, "audio_analysis")

    make_event(
        db,
        patient.id,
        "video_analysis",
        seconds=60,
        job_id="video-job-1",
        severity="low",
    )

    high = make_event(
        db,
        patient.id,
        "video_analysis",
        seconds=61,
        job_id="video-job-1",
        severity="high",
    )

    result = correlate(db, patient.id)

    assert len(result) == 1
    assert high.id in result[0].payload["source_event_ids"]


def test_correlation_idempotency(db):
    patient = make_patient(db)

    make_event(db, patient.id, "audio_analysis")
    make_event(db, patient.id, "video_analysis", seconds=60)

    assert len(correlate(db, patient.id)) == 1
    assert correlate(db, patient.id) == []
    assert correlate(db, patient.id) == []


def test_new_triple_after_existing_pair(db):
    patient = make_patient(db)

    make_event(db, patient.id, "audio_analysis")
    make_event(db, patient.id, "video_analysis", seconds=60)

    first = correlate(db, patient.id)

    assert len(first) == 1
    assert first[0].payload["source_count"] == 2

    make_event(db, patient.id, "vital_signs", seconds=120)

    second = correlate(db, patient.id)

    assert len(second) == 1
    assert second[0].payload["source_count"] == 3

    assert correlate(db, patient.id) == []


def test_invalid_window(db):
    patient = make_patient(db)

    with pytest.raises(ValueError):
        correlate(db, patient.id, window=0)

    with pytest.raises(ValueError):
        correlate(db, patient.id, window=61)


def test_missing_patient(db):
    with pytest.raises(ValueError, match="Patient not found"):
        correlate(db, "nonexistent")
