"""Testes do resumo de sinais vitais (dashboard/vitals_summary.py): funcoes puras, sem Streamlit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.vitals_summary import build_vitals_summary, format_vital  # noqa: E402


def _measurement(fc, spo2, pas, pad, measured_at="2026-11-23T12:06:54Z"):
    return {
        "id": "m-1",
        "patient_id": "pat-1",
        "measured_at": measured_at,
        "heart_rate_bpm": fc,
        "spo2_percent": spo2,
        "systolic_mmhg": pas,
        "diastolic_mmhg": pad,
        "source": "synthetic_simulator",
        "is_synthetic": True,
    }


def _critical_vital_event():
    return {
        "id": "ev-1",
        "source": "vital_signs",
        "event_type": "synthetic_vital_sign_anomaly",
        "severity": "critical",
        "payload": {
            "detections": [
                {"metric": "heart_rate_bpm", "value": 148.0, "severity": "critical",
                 "reason": "fora da faixa critica demonstrativa"},
                {"metric": "spo2_percent", "value": 84.0, "severity": "critical",
                 "reason": "abaixo do limite critico demonstrativo"},
                {"metric": "systolic_mmhg", "value": 78.0, "severity": "critical",
                 "reason": "fora da faixa critica demonstrativa"},
                {"metric": "diastolic_mmhg", "value": 48.0, "severity": "high",
                 "reason": "fora da faixa de atencao demonstrativa"},
            ],
        },
    }


def _critical_alert():
    return {"id": "al-1", "event_id": "ev-1", "severity": "critical", "status": "open"}


# ---------- Caso critico: valores com unidade, regras com motivo, conclusao ----------


def test_critical_measurement_shows_values_with_units():
    result = {
        "measurement": _measurement(148.0, 84.0, 78.0, 48.0),
        "events": [_critical_vital_event()],
        "alerts": [_critical_alert()],
    }
    summary = build_vitals_summary(result)
    assert summary["values"] == {
        "FC": "148 bpm",
        "SpO2": "84 %",
        "PAS": "78 mmHg",
        "PAD": "48 mmHg",
    }
    assert summary["measured_at"] == "23/11/2026 12:06"
    assert summary["source"] == "synthetic_simulator"


def test_critical_measurement_lists_each_rule_with_reason_in_pt_br():
    result = {
        "measurement": _measurement(148.0, 84.0, 78.0, 48.0),
        "events": [_critical_vital_event()],
        "alerts": [_critical_alert()],
    }
    rules = build_vitals_summary(result)["rules"]
    assert len(rules) == 4
    assert rules[0] == {
        "Medida": "Frequência cardíaca (FC)",
        "Valor": "148 bpm",
        "Severidade": "Crítica",
        "Motivo": "fora da faixa crítica demonstrativa",
    }
    assert rules[1]["Motivo"] == "abaixo do limite crítico demonstrativo"
    assert rules[1]["Medida"] == "SpO2"
    assert rules[3]["Severidade"] == "Alta"
    assert rules[3]["Motivo"] == "fora da faixa de atenção demonstrativa"


def test_critical_measurement_conclusion_counts_rules_and_alerts():
    result = {
        "measurement": _measurement(148.0, 84.0, 78.0, 48.0),
        "events": [_critical_vital_event()],
        "alerts": [_critical_alert()],
    }
    summary = build_vitals_summary(result)
    assert summary["conclusion"] == "4 regras disparadas: 1 evento crítico e 1 alerta aberto."
    assert "crítico" in summary["conclusion"]
    assert "1 alerta aberto" in summary["conclusion"]
    assert summary["triggered"] is True
    assert summary["event_count"] == 1
    assert summary["alert_count"] == 1


# ---------- Medicao normal ----------


def test_normal_measurement_without_events_is_within_rules():
    result = {"measurement": _measurement(72.0, 98.0, 120.0, 80.0), "events": [], "alerts": []}
    summary = build_vitals_summary(result)
    assert summary["conclusion"] == "Medição dentro das regras demonstrativas."
    assert summary["triggered"] is False
    assert summary["rules"] == []
    assert summary["trends"] == []
    assert summary["event_count"] == 0
    assert summary["alert_count"] == 0


def test_missing_result_does_not_raise():
    summary = build_vitals_summary(None)
    assert summary["values"]["FC"] == "—"
    assert summary["triggered"] is False


def test_format_vital_adds_unit_and_handles_missing_value():
    assert format_vital("spo2_percent", 84.0) == "84 %"
    assert format_vital("heart_rate_bpm", None) == "—"


# ---------- Tendencia temporal ----------


def test_rising_heart_rate_trend_uses_pt_br_label_and_value_sequence():
    trend_event = {
        "id": "ev-2",
        "source": "vital_trends",
        "event_type": "synthetic_vital_trend_anomaly",
        "severity": "medium",
        "payload": {
            "window_size": 4,
            "detections": [
                {
                    "code": "rising_heart_rate",
                    "metric": "heart_rate_bpm",
                    "severity": "medium",
                    "values": [80.0, 90.0, 100.0, 110.0],
                    "reason": "frequencia cardiaca em alta na janela recente",
                }
            ],
        },
    }
    result = {
        "measurement": _measurement(110.0, 98.0, 120.0, 80.0),
        "events": [trend_event],
        "alerts": [{"id": "al-2", "event_id": "ev-2", "severity": "medium", "status": "open"}],
    }
    summary = build_vitals_summary(result)
    assert summary["rules"] == []
    assert len(summary["trends"]) == 1
    trend = summary["trends"][0]
    assert trend["Tendência"] == "Frequência cardíaca em alta"
    assert trend["Medida"] == "Frequência cardíaca (FC)"
    assert trend["Valores (do mais antigo ao mais recente)"] == "80 → 90 → 100 → 110"
    assert trend["Severidade"] == "Média"
    assert summary["triggered"] is True
    assert "1 tendência identificada" in summary["conclusion"]
