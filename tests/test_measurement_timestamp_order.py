from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio

FIXED_NOW = datetime(2026, 11, 23, 12, 0, 0, tzinfo=UTC)
HEART_RATES = [70, 82, 94, 106]


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:  # SQLite devolve datetime sem fuso
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


@pytest.fixture
def fixed_now(monkeypatch: pytest.MonkeyPatch) -> datetime:
    monkeypatch.setattr("app.services.clinical_flow.utcnow", lambda: FIXED_NOW)
    return FIXED_NOW


async def _create_patient(client: AsyncClient, code: str) -> dict:
    response = await client.post(
        "/api/v1/patients",
        json={
            "code": code,
            "alias": f"Paciente {code}",
            "birth_year": 1990,
            "is_synthetic": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _post_heart_rates(client: AsyncClient, patient_id: str, heart_rates: list[int]) -> list[dict]:
    responses = []
    for heart_rate in heart_rates:
        response = await client.post(
            f"/api/v1/patients/{patient_id}/measurements",
            json={"heart_rate_bpm": heart_rate, "is_synthetic": True},
        )
        assert response.status_code == 201, response.text
        responses.append(response.json())
    return responses


async def test_empate_de_horario_mantem_evento_de_tendencia_no_quarto_envio(
    client: AsyncClient,
    fixed_now: datetime,
) -> None:
    for i in range(1, 6):
        patient = await _create_patient(client, f"MG-EMPATE-{i:02d}")
        responses = await _post_heart_rates(client, patient["id"], HEART_RATES)

        assert all(item["events"] == [] for item in responses[:3]), f"iteração {i}"
        last = responses[-1]
        assert len(last["events"]) == 1, f"iteração {i}"
        assert last["events"][0]["source"] == "vital_trends", f"iteração {i}"
        assert last["events"][0]["event_type"] == "synthetic_vital_trend_anomaly", f"iteração {i}"
        assert len(last["alerts"]) == 1, f"iteração {i}"


async def test_medicoes_com_mesmo_utcnow_ficam_estritamente_crescentes(
    client: AsyncClient,
    patient: dict,
    fixed_now: datetime,
) -> None:
    responses = await _post_heart_rates(client, patient["id"], HEART_RATES)

    sent_times = [_parse(item["measurement"]["measured_at"]) for item in responses]
    assert sent_times[0] == FIXED_NOW
    assert all(a < b for a, b in zip(sent_times, sent_times[1:]))

    listing = await client.get(f"/api/v1/patients/{patient['id']}/measurements")
    assert listing.status_code == 200, listing.text
    rows = listing.json()
    # A listagem da API é decrescente por measured_at.
    assert [row["heart_rate_bpm"] for row in rows] == [106, 94, 82, 70]

    ascending = sorted(rows, key=lambda row: _parse(row["measured_at"]))
    assert [row["heart_rate_bpm"] for row in ascending] == [70, 82, 94, 106]
    listed_times = [_parse(row["measured_at"]) for row in ascending]
    assert all(a < b for a, b in zip(listed_times, listed_times[1:]))
    assert listed_times == sent_times


async def test_measured_at_explicito_e_respeitado_mesmo_anterior_ao_ultimo(
    client: AsyncClient,
    patient: dict,
    fixed_now: datetime,
) -> None:
    patient_id = patient["id"]
    first = await client.post(
        f"/api/v1/patients/{patient_id}/measurements",
        json={"heart_rate_bpm": 70, "is_synthetic": True},
    )
    assert first.status_code == 201, first.text
    assert _parse(first.json()["measurement"]["measured_at"]) == FIXED_NOW

    explicit = FIXED_NOW - timedelta(hours=1)
    response = await client.post(
        f"/api/v1/patients/{patient_id}/measurements",
        json={
            "measured_at": explicit.isoformat(),
            "heart_rate_bpm": 82,
            "is_synthetic": True,
        },
    )
    assert response.status_code == 201, response.text
    assert _parse(response.json()["measurement"]["measured_at"]) == explicit


async def test_pacientes_diferentes_nao_se_afetam_no_mesmo_instante(
    client: AsyncClient,
    fixed_now: datetime,
) -> None:
    patient_a = await _create_patient(client, "MG-ISO-A")
    patient_b = await _create_patient(client, "MG-ISO-B")

    a_responses = await _post_heart_rates(client, patient_a["id"], [70, 82])
    assert _parse(a_responses[0]["measurement"]["measured_at"]) == FIXED_NOW
    assert _parse(a_responses[1]["measurement"]["measured_at"]) == FIXED_NOW + timedelta(microseconds=1)

    b_responses = await _post_heart_rates(client, patient_b["id"], [70, 82])
    assert _parse(b_responses[0]["measurement"]["measured_at"]) == FIXED_NOW
    assert _parse(b_responses[1]["measurement"]["measured_at"]) == FIXED_NOW + timedelta(microseconds=1)
