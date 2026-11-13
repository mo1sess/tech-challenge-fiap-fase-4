import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.db.migrate_correlation_keys import fingerprint, run_migration
from app.db.schema import check_schema


def test_legacy_schema_upgrade_preserves_history_and_is_repeatable():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE clinical_events (
            id TEXT PRIMARY KEY, patient_id TEXT, payload JSON, source TEXT,
            event_type TEXT, created_at TEXT)"""))
        for event_id in ("first", "second"):
            conn.execute(text("""INSERT INTO clinical_events VALUES
                (:id, 'patient', :payload, 'multimodal_correlation',
                'synthetic_multimodal_correlation_v2', :id)"""),
                {"id": event_id, "payload": json.dumps({"source_event_ids": ["b", "a"]})})
    with pytest.raises(RuntimeError, match="migration pending"):
        check_schema(engine)
    run_migration(engine)
    check_schema(engine)
    with engine.connect() as conn:
        before = conn.execute(text("SELECT * FROM clinical_events ORDER BY id")).all()
    # Simulate a key attached to a later historical duplicate.
    with engine.begin() as conn:
        conn.execute(text("UPDATE clinical_events SET correlation_key = NULL"))
        conn.execute(text("UPDATE clinical_events SET correlation_key = :key WHERE id = 'second'"),
                     {"key": before[0][-1]})
    run_migration(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT * FROM clinical_events ORDER BY id")).all() == before
    assert len(before) == 2
    assert before[0][-1] == fingerprint("patient", ["a", "b"])
    assert before[1][-1] is None
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("""INSERT INTO clinical_events (id, correlation_key)
            VALUES ('duplicate', :key)"""), {"key": before[0][-1]})
    engine.dispose()
