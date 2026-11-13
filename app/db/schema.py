"""Fail startup with an actionable message when an explicit upgrade is pending."""

from sqlalchemy import inspect


def check_schema(engine) -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("clinical_events")}
    indexes = inspector.get_indexes("clinical_events")
    unique_key = any(
        index["unique"] and index["column_names"] == ["correlation_key"]
        for index in indexes
    )
    if "correlation_key" not in columns or not unique_key:
        raise RuntimeError(
            "Database migration pending: clinical_events.correlation_key requires "
            "a nullable column and unique index. Run: docker compose run --rm "
            "--no-deps api python -m app.db.migrate_correlation_keys "
            "then restart the API. Existing data must be preserved."
        )
