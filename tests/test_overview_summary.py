"""Testes do resumo da Visao geral (dashboard/overview_summary.py): funcoes puras, sem Streamlit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.overview_summary import (  # noqa: E402
    build_demo_summary,
    compact_alerts,
    open_alerts_by_severity,
)

PATIENTS = [{"id": "pat-1", "code": "MG-001", "alias": "Paciente Alfa"}]


def _alert(severity, status="open", message="Revisar evento.", patient_id="pat-1"):
    return {
        "id": f"al-{severity}-{status}",
        "event_id": "ev-x",
        "patient_id": patient_id,
        "severity": severity,
        "status": status,
        "message": message,
        "created_at": "2026-11-23T12:06:54Z",
        "acknowledged_at": None,
    }


# ---------- Contagem de alertas abertos por severidade ----------


def test_open_alerts_counted_by_severity_ignoring_non_open_status():
    alerts = [
        _alert("critical", "open"),
        _alert("critical", "open"),
        _alert("critical", "resolved"),
        _alert("high", "open"),
        _alert("high", "acknowledged"),
        _alert("medium", "open"),
        _alert("low", "open"),
        _alert("low", "acknowledged"),
    ]
    assert open_alerts_by_severity(alerts) == {"Crítica": 2, "Alta": 1, "Média": 1, "Baixa": 1}


def test_open_alerts_order_and_zero_counts_when_empty():
    assert open_alerts_by_severity([]) == {"Crítica": 0, "Alta": 0, "Média": 0, "Baixa": 0}
    assert list(open_alerts_by_severity(None)) == ["Crítica", "Alta", "Média", "Baixa"]


def test_open_alerts_without_status_field_count_as_open():
    assert open_alerts_by_severity([{"severity": "high"}])["Alta"] == 1


# ---------- Tabela de alertas ----------


def test_compact_alerts_shows_patient_code_when_patients_given():
    rows = compact_alerts([_alert("critical")], PATIENTS)
    assert rows == [
        {
            "Quando": "23/11/2026 12:06",
            "Paciente": "MG-001",
            "Severidade": "Crítica",
            "Status": "Aberto",
            "Mensagem": "Revisar evento",
        }
    ]


def test_compact_alerts_mixed_statuses_and_severities_translated():
    rows = compact_alerts(
        [_alert("high", "acknowledged"), _alert("medium", "open"), _alert("low", "resolved")],
        PATIENTS,
    )
    assert [r["Status"] for r in rows] == ["Reconhecido", "Aberto", "Resolvido"]
    assert [r["Severidade"] for r in rows] == ["Alta", "Média", "Baixa"]


def test_compact_alerts_message_keeps_only_first_sentence_and_translates_severity():
    message = "Revisar evento sintetico de sinais vitais (critical). Dado sintetico, sem uso clinico."
    rows = compact_alerts([_alert("critical", message=message)], PATIENTS)
    assert rows[0]["Mensagem"] == "Revisar evento sintetico de sinais vitais (crítica)"
    assert "sem uso clinico" not in rows[0]["Mensagem"]


def test_compact_alerts_without_patients_falls_back_to_id_prefix():
    rows = compact_alerts([_alert("low", patient_id="pat-123456789")])
    assert rows[0]["Paciente"] == "pat-1234"


# ---------- Resultado da demo de alerta ----------


def _demo_critical():
    return {
        "patient": {"id": "pat-1", "code": "MG-DEMO-01", "alias": "Paciente Demo"},
        "result": {
            "measurement": {
                "measured_at": "2026-11-23T12:06:54Z",
                "source": "demo_button",
                "heart_rate_bpm": 148.0,
                "spo2_percent": 84.0,
                "systolic_mmhg": 78.0,
                "diastolic_mmhg": 48.0,
            },
            "events": [
                {
                    "id": "ev-1",
                    "source": "vital_signs",
                    "severity": "critical",
                    "payload": {
                        "detections": [
                            {"metric": "heart_rate_bpm", "value": 148.0, "severity": "critical",
                             "reason": "fora da faixa critica demonstrativa"},
                        ]
                    },
                }
            ],
            "alerts": [{"id": "al-1", "event_id": "ev-1", "severity": "critical", "status": "open"}],
        },
    }


def test_demo_summary_resumes_alert_with_patient_severity_and_values():
    summary = build_demo_summary(_demo_critical())
    assert summary["patient"] == "MG-DEMO-01"
    assert summary["patient_alias"] == "Paciente Demo"
    assert summary["severity"] == "Crítica"
    assert summary["values"]["FC"] == "148 bpm"
    assert summary["rules"][0]["Motivo"] == "fora da faixa crítica demonstrativa"
    assert summary["triggered"] is True
    assert summary["conclusion"] == "1 regra disparada: 1 evento crítico e 1 alerta aberto."


def test_demo_summary_without_triggers_keeps_within_rules_conclusion():
    demo = {
        "patient": {"code": "MG-DEMO-02", "alias": "Paciente Demo 2"},
        "result": {
            "measurement": {"measured_at": "2026-11-23T12:06:54Z", "source": "demo_button",
                            "heart_rate_bpm": 72.0, "spo2_percent": 98.0,
                            "systolic_mmhg": 120.0, "diastolic_mmhg": 80.0},
            "events": [],
            "alerts": [],
        },
    }
    summary = build_demo_summary(demo)
    assert summary["severity"] == "—"
    assert summary["conclusion"] == "Medição dentro das regras demonstrativas."
    assert summary["triggered"] is False


def test_demo_summary_missing_input_does_not_raise():
    summary = build_demo_summary(None)
    assert summary["patient"] == "—"
    assert summary["severity"] == "—"
