
"""Repeatable migration for multimodal correlation uniqueness."""

import hashlib
import json

from sqlalchemy import text

from app.core.config import get_settings
from app.main import build_engine


def fingerprint(patient_id: str, source_ids: list[str]) -> str:
    normalized = sorted(source_ids)
    raw = json.dumps(
        ["synthetic_multimodal_correlation_v2", patient_id, normalized],
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_migration(engine=None) -> None:
    owns_engine = engine is None
    engine = engine if engine is not None else build_engine(get_settings())

    try:
        with engine.begin() as connection:
            dialect = connection.dialect.name

            if dialect == "postgresql":
                # Serialize migrations and prevent concurrent writes during backfill.
                connection.execute(text("LOCK TABLE clinical_events IN ACCESS EXCLUSIVE MODE"))
                connection.execute(text(
                    "ALTER TABLE clinical_events "
                    "ADD COLUMN IF NOT EXISTS correlation_key VARCHAR(64)"
                ))
            elif dialect == "sqlite":
                columns = connection.execute(
                    text("PRAGMA table_info(clinical_events)")
                ).all()

                if not any(column[1] == "correlation_key" for column in columns):
                    connection.execute(text(
                        "ALTER TABLE clinical_events "
                        "ADD COLUMN correlation_key VARCHAR(64)"
                    ))
            else:
                raise RuntimeError(f"Unsupported database: {dialect}")

            rows = connection.execute(text("""
                SELECT id, patient_id, payload, correlation_key
                FROM clinical_events
                WHERE source = 'multimodal_correlation'
                  AND event_type = 'synthetic_multimodal_correlation_v2'
                ORDER BY created_at, id
            """)).mappings().all()

            # Clear managed keys first so an existing unique index cannot reject
            # reassignment to the oldest historical duplicate on a repeated run.
            for row in rows:
                connection.execute(text(
                    "UPDATE clinical_events SET correlation_key = NULL WHERE id = :id"
                ), {"id": row["id"]})

            used_keys = set()
            duplicates = 0
            updated = 0

            for row in rows:
                payload = row["payload"] or {}

                if isinstance(payload, str):
                    payload = json.loads(payload)

                source_ids = payload.get("source_event_ids", [])

                if not source_ids:
                    continue

                key = fingerprint(row["patient_id"], source_ids)

                if key in used_keys:
                    # Keep historical duplicates, with a NULL key.
                    connection.execute(text("""
                        UPDATE clinical_events
                        SET correlation_key = NULL
                        WHERE id = :id
                    """), {"id": row["id"]})
                    duplicates += 1
                    continue

                used_keys.add(key)

                connection.execute(text("""
                    UPDATE clinical_events
                    SET correlation_key = :key
                    WHERE id = :id
                """), {"key": key, "id": row["id"]})

                updated += 1

            connection.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                ix_clinical_events_correlation_key
                ON clinical_events (correlation_key)
            """))

            print(
                f"Migration complete: {updated} correlations indexed; "
                f"{duplicates} historical duplicates preserved."
            )

    finally:
        if owns_engine:
            engine.dispose()


if __name__ == "__main__":
    run_migration()
