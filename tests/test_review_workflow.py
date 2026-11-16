import pytest
from sqlalchemy import create_engine, inspect
from app.db.base import Base
from app.db.migrate_alert_reviews import run_migration


@pytest.mark.anyio
async def test_review_history_transitions_and_isolation(client, patient):
    response = await client.post(f"/api/v1/patients/{patient['id']}/measurements", json={"heart_rate_bpm": 145})
    alert = response.json()["alerts"][0]
    path = f"/api/v1/alerts/{alert['id']}"
    assert alert["status"] == "open"
    assert (await client.patch(path, json={"status": "acknowledged", "reviewer": "Revisor fictício A"})).status_code == 200
    assert (await client.patch(path, json={"status": "acknowledged"})).status_code == 200
    assert (await client.patch(path, json={"status": "resolved", "note": "Revisão simulada concluída"})).status_code == 200
    assert (await client.patch(path, json={"status": "acknowledged"})).status_code == 409
    assert (await client.patch(path, json={"status": "open"})).status_code == 422
    history = (await client.get(path + "/history", params={"patient_id": patient['id']})).json()
    assert len(history) == 2
    assert history[0]["reviewer"] == "Revisor fictício A"
    assert history[1]["previous_status"] == "acknowledged"
    assert all(h["created_at"] for h in history)
    assert (await client.get(path + "/history", params={"patient_id": "other"})).status_code == 404
    assert (await client.get("/api/v1/alerts", params={"patient_id": "other"})).json() == []


def test_additive_migration_repeatable():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    run_migration(engine)
    run_migration(engine)
    assert inspect(engine).has_table("alert_review_actions")
