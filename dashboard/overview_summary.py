"""Resumo legivel da Visao geral: alertas e demo de alerta vital (funcoes puras)."""

from __future__ import annotations

try:
    from .common_summary import (
        ALERT_STATUS_LABELS,
        SEVERITY_ORDER,
        events_alerts_phrase,
        format_datetime,
        patient_label,
        severity_label,
    )
    from .vitals_summary import build_vitals_summary
except ImportError:  # carregado como modulo de topo pelo Streamlit
    from common_summary import (
        ALERT_STATUS_LABELS,
        SEVERITY_ORDER,
        events_alerts_phrase,
        format_datetime,
        patient_label,
        severity_label,
    )
    from vitals_summary import build_vitals_summary


def open_alerts_by_severity(alerts: list[dict] | None) -> dict[str, int]:
    """Contagem de alertas abertos por severidade, na ordem Crítica, Alta, Média, Baixa."""
    counts = {severity_label(s): 0 for s in SEVERITY_ORDER}
    for alert in alerts or []:
        if alert.get("status", "open") != "open":
            continue
        label = severity_label(alert.get("severity"))
        counts[label] = counts.get(label, 0) + 1
    return counts


def build_demo_summary(demo: dict | None) -> dict:
    """Resume a resposta de POST /demo/vital-alert ({patient, result}).

    Retorno: {"patient": codigo, "patient_alias", **build_vitals_summary(result),
    "severity": rótulo da maior severidade ou "—", "conclusion"}.
    """
    demo = demo or {}
    patient = demo.get("patient") or {}
    result = demo.get("result") or {}
    summary = build_vitals_summary(result)
    severities = [e.get("severity") for e in result.get("events") or []]
    ranked = [s for s in SEVERITY_ORDER if s in severities]
    summary["patient"] = patient.get("code") or "—"
    summary["patient_alias"] = patient.get("alias") or "—"
    summary["severity"] = severity_label(ranked[0]) if ranked else "—"
    if not summary["triggered"] and (result.get("events") or result.get("alerts")):
        summary["conclusion"] = events_alerts_phrase(result.get("events"), result.get("alerts")).capitalize() + "."
    return summary


def _short_message(message: str | None, severity: str | None) -> str:
    """Corta o texto no primeiro '. ' (o resto e o aviso legal) e traduz '(critical)'."""
    if not message:
        return "—"
    text = message.split(". ", 1)[0].rstrip(".")
    if severity:
        text = text.replace(f"({severity})", f"({severity_label(severity).lower()})")
    return text


def compact_alerts(alerts: list[dict] | None, patients: list[dict] | None = None) -> list[dict]:
    """Linhas: Quando, Paciente (código), Severidade, Status, Mensagem."""
    return [
        {
            "Quando": format_datetime(a.get("created_at")),
            "Paciente": patient_label(a.get("patient_id"), patients),
            "Severidade": severity_label(a.get("severity")),
            "Status": ALERT_STATUS_LABELS.get(a.get("status"), str(a.get("status") or "—")),
            "Mensagem": _short_message(a.get("message"), a.get("severity")),
        }
        for a in alerts or []
    ]
