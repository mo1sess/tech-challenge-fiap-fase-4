"""Testes do resumo de operacoes (dashboard/operations_summary.py): prescricoes, movimentacoes e eventos compactos."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.operations_summary import (  # noqa: E402
    build_movement_summary,
    build_prescription_summary,
    compact_operation_events,
)

PATIENTS = [{"id": "pat-1", "code": "MG-001"}]


def _prescription_event(anomaly, severity="medium", previous_action=None):
    return {
        "id": "ev-p",
        "patient_id": "pat-1",
        "source": "prescription_analysis",
        "severity": severity,
        "payload": {"anomaly": anomaly, "previous_action": previous_action},
    }


def _movement_event(anomalies, severity="high"):
    return {
        "id": "ev-m",
        "patient_id": "pat-1",
        "source": "movement_analysis",
        "severity": severity,
        "payload": {"anomalies": anomalies, "requires_human_review": True},
    }


# ---------- Prescricao ----------


def test_prescription_without_inconsistency_is_registered_without_inconsistencies():
    result = {
        "prescription": {"action": "started", "medication_code": "MED-01", "recorded_at": "2026-11-23T12:00:00Z"},
        "events": [],
        "alerts": [],
    }
    summary = build_prescription_summary(result)
    assert summary["action"] == "Início"
    assert summary["medication"] == "MED-01"
    assert summary["recorded_at"] == "23/11/2026 12:00"
    assert summary["inconsistencies"] == []
    assert summary["event_count"] == 0
    assert summary["alert_count"] == 0
    assert "sem inconsistências" in summary["conclusion"]


def test_prescription_duplicate_start_is_listed_with_description_and_conclusion():
    result = {
        "prescription": {"action": "started", "medication_code": "MED-01", "recorded_at": "2026-11-23T12:00:00Z"},
        "events": [_prescription_event("duplicate_start", "medium", previous_action="started")],
        "alerts": [{"id": "al-p", "status": "open"}],
    }
    summary = build_prescription_summary(result)
    assert summary["previous_action"] == "Início"
    assert summary["inconsistencies"] == [
        {
            "Inconsistência": "Início duplicado",
            "Descrição": "A prescrição já estava ativa e foi iniciada novamente.",
            "Severidade": "Média",
        }
    ]
    assert summary["event_count"] == 1
    assert summary["alert_count"] == 1
    assert summary["conclusion"] == "1 inconsistência detectada: 1 evento de severidade média e 1 alerta aberto."


def test_prescription_action_without_active_prescription_has_no_previous_action():
    result = {
        "prescription": {"action": "stopped", "medication_code": "MED-02", "recorded_at": "2026-11-23T12:00:00Z"},
        "events": [_prescription_event("action_without_active_prescription", "medium", previous_action=None)],
        "alerts": [{"id": "al-p", "status": "open"}],
    }
    summary = build_prescription_summary(result)
    assert summary["action"] == "Suspensão"
    assert summary["previous_action"] == "—"
    assert summary["inconsistencies"][0]["Inconsistência"] == "Ação sem prescrição ativa"


def test_prescription_summary_none_does_not_raise():
    summary = build_prescription_summary(None)
    assert summary["action"] == "—"
    assert summary["inconsistencies"] == []


# ---------- Movimentacao ----------


def test_movement_summary_lists_each_anomaly_with_its_own_severity():
    result = {
        "movement": {"from_location": "Ala A", "to_location": "Ala B", "recorded_at": "2026-11-23T12:00:00Z"},
        "events": [
            _movement_event(
                [
                    {"code": "location_continuity_mismatch", "severity": "high"},
                    {"code": "rapid_repeated_transfer", "severity": "medium"},
                ],
                severity="high",
            )
        ],
        "alerts": [{"id": "al-m", "status": "open"}],
    }
    summary = build_movement_summary(result)
    assert summary["from"] == "Ala A"
    assert summary["to"] == "Ala B"
    assert summary["recorded_at"] == "23/11/2026 12:00"
    assert summary["inconsistencies"] == [
        {
            "Inconsistência": "Origem diferente do último destino",
            "Descrição": "A origem informada não coincide com o destino da movimentação anterior.",
            "Severidade": "Alta",
        },
        {
            "Inconsistência": "Transferência repetida em menos de 2 minutos",
            "Descrição": "Nova movimentação registrada menos de 2 minutos após a anterior.",
            "Severidade": "Média",
        },
    ]
    assert summary["conclusion"] == "2 inconsistências detectadas: 1 evento de severidade alta e 1 alerta aberto."


def test_movement_without_anomaly_is_registered_without_inconsistencies():
    result = {
        "movement": {"from_location": "Ala A", "to_location": "Ala B", "recorded_at": "2026-11-23T12:00:00Z"},
        "events": [],
        "alerts": [],
    }
    summary = build_movement_summary(result)
    assert summary["inconsistencies"] == []
    assert summary["conclusion"] == "Movimentação registrada sem inconsistências nas regras demonstrativas."


@pytest.mark.parametrize(
    ("code", "label"),
    [
        ("same_origin_destination", "Origem e destino iguais"),
        ("location_continuity_mismatch", "Origem diferente do último destino"),
        ("rapid_repeated_transfer", "Transferência repetida em menos de 2 minutos"),
    ],
)
def test_movement_codes_map_to_pt_br_labels(code, label):
    result = {"events": [_movement_event([{"code": code, "severity": "medium"}])]}
    assert build_movement_summary(result)["inconsistencies"][0]["Inconsistência"] == label


@pytest.mark.parametrize(
    ("code", "label"),
    [
        ("duplicate_start", "Início duplicado"),
        ("action_without_active_prescription", "Ação sem prescrição ativa"),
    ],
)
def test_prescription_codes_map_to_pt_br_labels(code, label):
    result = {"prescription": {"action": "changed"}, "events": [_prescription_event(code)]}
    assert build_prescription_summary(result)["inconsistencies"][0]["Inconsistência"] == label


# ---------- Eventos compactos ----------


def test_compact_operation_events_keeps_only_operation_sources_with_documented_columns():
    events = [
        {
            "id": "ev-t",
            "patient_id": "pat-1",
            "source": "vital_trends",
            "severity": "medium",
            "occurred_at": "2026-11-23T12:00:00Z",
            "title": "Tendencia demonstrativa em sinais vitais",
            "payload": {"detections": [{"code": "rising_heart_rate"}]},
        },
        {
            "id": "ev-p",
            "patient_id": "pat-1",
            "source": "prescription_analysis",
            "severity": "medium",
            "occurred_at": "2026-11-23T12:05:00Z",
            "title": "Sequencia demonstrativa de prescricao requer revisao",
            "payload": {"anomaly": "duplicate_start"},
        },
        {
            "id": "ev-m",
            "patient_id": "pat-1",
            "source": "movement_analysis",
            "severity": "high",
            "occurred_at": "2026-11-23T12:10:00Z",
            "title": "Movimentacao sintetica requer revisao",
            "payload": {
                "anomalies": [
                    {"code": "location_continuity_mismatch", "severity": "high"},
                    {"code": "rapid_repeated_transfer", "severity": "medium"},
                ]
            },
        },
        {
            "id": "ev-a",
            "patient_id": "pat-1",
            "source": "audio_analysis",
            "severity": "low",
            "occurred_at": "2026-11-23T12:15:00Z",
            "title": "Audio",
            "payload": {},
        },
        {
            "id": "ev-v",
            "patient_id": "pat-1",
            "source": "video_analysis",
            "severity": "high",
            "occurred_at": "2026-11-23T12:16:00Z",
            "title": "Video",
            "payload": {},
        },
    ]
    rows = compact_operation_events(events, PATIENTS)
    assert len(rows) == 3
    for row in rows:
        assert set(row) == {"Quando", "Paciente", "Origem", "Regras", "Severidade", "Título"}
    assert rows[0] == {
        "Quando": "23/11/2026 12:00",
        "Paciente": "MG-001",
        "Origem": "Tendência vital",
        "Regras": "Frequência cardíaca em alta",
        "Severidade": "Média",
        "Título": "Tendencia demonstrativa em sinais vitais",
    }
    assert rows[1]["Origem"] == "Prescrição"
    assert rows[1]["Regras"] == "Início duplicado"
    assert rows[2]["Origem"] == "Movimentação"
    assert rows[2]["Regras"] == "Origem diferente do último destino; Transferência repetida em menos de 2 minutos"
    assert rows[2]["Severidade"] == "Alta"


def test_compact_operation_events_empty_or_none_returns_empty_list():
    assert compact_operation_events([], PATIENTS) == []
    assert compact_operation_events(None) == []
