"""Resumo legivel de sinais vitais (medicao + regras + tendencias). Funcoes puras."""

from __future__ import annotations

from typing import Any

try:
    from .common_summary import events_alerts_phrase, format_datetime, format_number, plural, severity_label
except ImportError:  # carregado como modulo de topo pelo Streamlit
    from common_summary import events_alerts_phrase, format_datetime, format_number, plural, severity_label

METRIC_LABELS = {
    "heart_rate_bpm": "Frequência cardíaca (FC)",
    "spo2_percent": "SpO2",
    "systolic_mmhg": "Pressão sistólica (PAS)",
    "diastolic_mmhg": "Pressão diastólica (PAD)",
}
METRIC_UNITS = {"heart_rate_bpm": "bpm", "spo2_percent": "%", "systolic_mmhg": "mmHg", "diastolic_mmhg": "mmHg"}
# Motivos gravados por app/services/vital_signs.py (sem acento) -> pt-BR acentuado.
REASON_LABELS = {
    "fora da faixa critica demonstrativa": "fora da faixa crítica demonstrativa",
    "fora da faixa de atencao demonstrativa": "fora da faixa de atenção demonstrativa",
    "abaixo do limite critico demonstrativo": "abaixo do limite crítico demonstrativo",
    "abaixo do limite de atencao demonstrativo": "abaixo do limite de atenção demonstrativo",
    "requer revisao demonstrativa": "requer revisão demonstrativa",
}
TREND_LABELS = {
    "rising_heart_rate": "Frequência cardíaca em alta",
    "falling_spo2": "SpO2 em queda",
    "systolic_variability": "Variabilidade da pressão sistólica",
}
VITAL_SOURCE = "vital_signs"
TREND_SOURCE = "vital_trends"
TREND_VALUES_COLUMN = "Valores (do mais antigo ao mais recente)"


def format_vital(metric: str, value: Any) -> str:
    text = format_number(value)
    unit = METRIC_UNITS.get(metric)
    return f"{text} {unit}" if unit and text != "—" else text


def _rule_rows(events: list[dict]) -> list[dict]:
    rows = []
    for event in events:
        if event.get("source") != VITAL_SOURCE:
            continue
        for item in (event.get("payload") or {}).get("detections") or []:
            metric = item.get("metric")
            rows.append(
                {
                    "Medida": METRIC_LABELS.get(metric, str(metric or "—")),
                    "Valor": format_vital(metric, item.get("value")),
                    "Severidade": severity_label(item.get("severity")),
                    "Motivo": REASON_LABELS.get(item.get("reason"), str(item.get("reason") or "—")),
                }
            )
    return rows


def _trend_rows(events: list[dict]) -> list[dict]:
    rows = []
    for event in events:
        if event.get("source") != TREND_SOURCE:
            continue
        for item in (event.get("payload") or {}).get("detections") or []:
            metric = item.get("metric")
            values = item.get("values") or []
            rows.append(
                {
                    "Tendência": TREND_LABELS.get(item.get("code"), str(item.get("code") or "—")),
                    "Medida": METRIC_LABELS.get(metric, str(metric or "—")),
                    TREND_VALUES_COLUMN: " → ".join(format_number(v) for v in values) or "—",
                    "Severidade": severity_label(item.get("severity")),
                    "Motivo": str(item.get("reason") or "—"),
                }
            )
    return rows


def build_vitals_summary(result: dict | None) -> dict:
    """Resume a resposta de POST /patients/{id}/measurements (ou o `result` do demo).

    Retorno: {"measured_at", "source", "values": {"FC","SpO2","PAS","PAD": "valor unidade"},
    "rules": [{Medida, Valor, Severidade, Motivo}],
    "trends": [{Tendência, Medida, "Valores (do mais antigo ao mais recente)", Severidade, Motivo}],
    "event_count", "alert_count", "triggered": bool, "conclusion"}.
    """
    result = result or {}
    measurement = result.get("measurement") or {}
    events = result.get("events") or []
    alerts = result.get("alerts") or []

    values = {
        "FC": format_vital("heart_rate_bpm", measurement.get("heart_rate_bpm")),
        "SpO2": format_vital("spo2_percent", measurement.get("spo2_percent")),
        "PAS": format_vital("systolic_mmhg", measurement.get("systolic_mmhg")),
        "PAD": format_vital("diastolic_mmhg", measurement.get("diastolic_mmhg")),
    }
    rules = _rule_rows(events)
    trends = _trend_rows(events)
    if rules or trends:
        parts = []
        if rules:
            parts.append(plural(len(rules), "regra disparada", "regras disparadas"))
        if trends:
            parts.append(plural(len(trends), "tendência identificada", "tendências identificadas"))
        conclusion = f"{' e '.join(parts)}: {events_alerts_phrase(events, alerts)}."
    else:
        conclusion = "Medição dentro das regras demonstrativas."
    return {
        "measured_at": format_datetime(measurement.get("measured_at")),
        "source": measurement.get("source") or "—",
        "values": values,
        "rules": rules,
        "trends": trends,
        "event_count": len(events),
        "alert_count": len(alerts),
        "triggered": bool(rules or trends),
        "conclusion": conclusion,
    }
