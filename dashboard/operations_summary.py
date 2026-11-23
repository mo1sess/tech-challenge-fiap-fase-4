"""Resumo legivel de prescricoes e movimentacoes sinteticas (funcoes puras)."""

from __future__ import annotations

try:
    from .common_summary import events_alerts_phrase, format_datetime, patient_label, plural, severity_label
    from .vitals_summary import TREND_LABELS
except ImportError:  # carregado como modulo de topo pelo Streamlit
    from common_summary import events_alerts_phrase, format_datetime, patient_label, plural, severity_label
    from vitals_summary import TREND_LABELS

# PrescriptionCreate.action
ACTION_LABELS = {"started": "Início", "changed": "Alteração", "stopped": "Suspensão"}
# Codigos de app/services/prescription_flow.py e movement_flow.py
INCONSISTENCY_LABELS = {
    "duplicate_start": "Início duplicado",
    "action_without_active_prescription": "Ação sem prescrição ativa",
    "same_origin_destination": "Origem e destino iguais",
    "location_continuity_mismatch": "Origem diferente do último destino",
    "rapid_repeated_transfer": "Transferência repetida em menos de 2 minutos",
}
INCONSISTENCY_DESCRIPTIONS = {
    "duplicate_start": "A prescrição já estava ativa e foi iniciada novamente.",
    "action_without_active_prescription": "Alteração ou suspensão sem prescrição ativa anterior para este medicamento.",
    "same_origin_destination": "A movimentação saiu e chegou ao mesmo local.",
    "location_continuity_mismatch": "A origem informada não coincide com o destino da movimentação anterior.",
    "rapid_repeated_transfer": "Nova movimentação registrada menos de 2 minutos após a anterior.",
}
EVENT_SOURCE_LABELS = {
    "vital_trends": "Tendência vital",
    "prescription_analysis": "Prescrição",
    "movement_analysis": "Movimentação",
}
OPERATION_SOURCES = set(EVENT_SOURCE_LABELS)


def _row(code, severity) -> dict:
    return {
        "Inconsistência": INCONSISTENCY_LABELS.get(code, str(code or "—")),
        "Descrição": INCONSISTENCY_DESCRIPTIONS.get(code, "—"),
        "Severidade": severity_label(severity),
    }


def _conclusion(rows: list[dict], events: list[dict], alerts: list[dict], what: str) -> str:
    if not rows:
        return f"{what} registrada sem inconsistências nas regras demonstrativas."
    return f"{plural(len(rows), 'inconsistência detectada', 'inconsistências detectadas')}: {events_alerts_phrase(events, alerts)}."


def build_prescription_summary(result: dict | None) -> dict:
    """Resume POST /patients/{id}/prescriptions/evaluate ({prescription, events, alerts}).

    Retorno: {"action": "Início"/"Alteração"/"Suspensão", "medication", "recorded_at",
    "previous_action": rótulo ou "—", "inconsistencies": [{Inconsistência, Descrição,
    Severidade}], "event_count", "alert_count", "conclusion"}.
    """
    result = result or {}
    prescription = result.get("prescription") or {}
    events = result.get("events") or []
    alerts = result.get("alerts") or []
    rows = []
    previous = None
    for event in events:
        payload = event.get("payload") or {}
        if payload.get("anomaly"):
            rows.append(_row(payload["anomaly"], event.get("severity")))
        previous = payload.get("previous_action") or previous
    return {
        "action": ACTION_LABELS.get(prescription.get("action"), str(prescription.get("action") or "—")),
        "medication": prescription.get("medication_code") or "—",
        "recorded_at": format_datetime(prescription.get("recorded_at")),
        "previous_action": ACTION_LABELS.get(previous, "—") if previous else "—",
        "inconsistencies": rows,
        "event_count": len(events),
        "alert_count": len(alerts),
        "conclusion": _conclusion(rows, events, alerts, "Prescrição"),
    }


def build_movement_summary(result: dict | None) -> dict:
    """Resume POST /patients/{id}/movements ({movement, events, alerts}).

    Retorno: {"from", "to", "recorded_at", "inconsistencies": [{Inconsistência, Descrição,
    Severidade}], "event_count", "alert_count", "conclusion"}.
    """
    result = result or {}
    movement = result.get("movement") or {}
    events = result.get("events") or []
    alerts = result.get("alerts") or []
    rows = []
    for event in events:
        for item in (event.get("payload") or {}).get("anomalies") or []:
            rows.append(_row(item.get("code"), item.get("severity")))
    return {
        "from": movement.get("from_location") or "—",
        "to": movement.get("to_location") or "—",
        "recorded_at": format_datetime(movement.get("recorded_at")),
        "inconsistencies": rows,
        "event_count": len(events),
        "alert_count": len(alerts),
        "conclusion": _conclusion(rows, events, alerts, "Movimentação"),
    }


def _event_rules(event: dict) -> str:
    payload = event.get("payload") or {}
    source = event.get("source")
    if source == "prescription_analysis":
        codes = [payload.get("anomaly")]
    elif source == "movement_analysis":
        codes = [a.get("code") for a in payload.get("anomalies") or []]
    else:
        codes = [d.get("code") for d in payload.get("detections") or []]
    labels = [INCONSISTENCY_LABELS.get(c) or TREND_LABELS.get(c) or str(c) for c in codes if c]
    return "; ".join(labels) or "—"


def compact_operation_events(events: list[dict] | None, patients: list[dict] | None = None) -> list[dict]:
    """Linhas (tendencia vital, prescricao, movimentacao): Quando, Paciente, Origem, Regras, Severidade, Título."""
    rows = []
    for event in events or []:
        if event.get("source") not in OPERATION_SOURCES:
            continue
        rows.append(
            {
                "Quando": format_datetime(event.get("occurred_at") or event.get("created_at")),
                "Paciente": patient_label(event.get("patient_id"), patients),
                "Origem": EVENT_SOURCE_LABELS[event["source"]],
                "Regras": _event_rules(event),
                "Severidade": severity_label(event.get("severity")),
                "Título": event.get("title") or "—",
            }
        )
    return rows
