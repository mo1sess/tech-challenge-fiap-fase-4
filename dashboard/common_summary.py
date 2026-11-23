"""Helpers comuns dos resumos legiveis do dashboard (funcoes puras, sem streamlit/requests)."""

from __future__ import annotations

from typing import Any

SEVERITY_LABELS = {"low": "Baixa", "medium": "Média", "high": "Alta", "critical": "Crítica"}
# Mesma severidade como adjetivo masculino ("1 evento crítico").
SEVERITY_ADJECTIVES = {"low": "de severidade baixa", "medium": "de severidade média", "high": "de severidade alta", "critical": "crítico"}
SEVERITY_ORDER = ("critical", "high", "medium", "low")
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

JOB_STATUS_LABELS = {
    "queued": "Na fila",
    "pending": "Na fila",
    "processing": "Processando",
    "completed": "Concluído",
    "failed": "Falhou",
}
ALERT_STATUS_LABELS = {"open": "Aberto", "acknowledged": "Reconhecido", "resolved": "Resolvido"}
JOB_TYPE_LABELS = {"audio_analysis": "Áudio", "video_analysis": "Vídeo"}
MEDIA_KIND_LABELS = {"audio": "Áudio", "video": "Vídeo"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _num(value: Any, decimals: int = 1) -> str | None:
    if not _is_number(value):
        return None
    return f"{value:.{decimals}f}".replace(".", ",")


def format_number(value: Any, decimals: int | None = None) -> str:
    """Numero pt-BR. Sem `decimals`: inteiro se for inteiro, senao 1 casa."""
    if not _is_number(value):
        return "—"
    if decimals is None:
        decimals = 0 if float(value).is_integer() else 1
    return _num(value, decimals) or "—"


def format_seconds(value: Any) -> str:
    text = _num(value, 1)
    return f"{text} s" if text else "—"


def format_percent(value: Any) -> str:
    """Recebe razao 0..1 e devolve percentual pt-BR."""
    text = _num(value * 100 if _is_number(value) else value, 1)
    return f"{text} %" if text else "—"


def format_percent_points(value: Any, decimals: int = 1) -> str:
    """Recebe valor ja em pontos percentuais (ex.: 0.0671) e devolve '0,1 %'."""
    text = _num(value, decimals)
    return f"{text} %" if text else "—"


def format_decimal(value: Any, decimals: int = 3) -> str:
    return _num(value, decimals) or "—"


def format_datetime(value: Any) -> str:
    """'2026-11-23T12:06:54.79Z' -> '23/11/2026 12:06' (sem conversao de fuso)."""
    if not isinstance(value, str) or len(value) < 16 or value[4:5] != "-":
        return "—"
    return f"{value[8:10]}/{value[5:7]}/{value[0:4]} {value[11:16]}"


def format_bytes(value: Any) -> str:
    if not _is_number(value) or value < 0:
        return "—"
    if value < 1024:
        return f"{int(value)} B"
    if value < 1024 * 1024:
        return f"{_num(value / 1024, 1)} KB"
    return f"{_num(value / (1024 * 1024), 1)} MB"


def short_hash(value: Any, size: int = 12) -> str:
    return str(value)[:size] if value else "—"


def severity_label(value: Any) -> str:
    return SEVERITY_LABELS.get(value, str(value or "—"))


def job_status_label(value: Any) -> str:
    return JOB_STATUS_LABELS.get(value, str(value or "—"))


def patient_label(patient_id: str | None, patients: list[dict] | None) -> str:
    for patient in patients or []:
        if patient.get("id") == patient_id:
            return str(patient.get("code") or patient.get("alias") or patient_id)
    return str(patient_id)[:8] if patient_id else "—"


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    return f"{count} {singular if count == 1 else (plural_form or singular + 's')}"


def highest_severity(severities: list[Any]) -> str | None:
    known = [s for s in severities if s in SEVERITY_RANK]
    return max(known, key=SEVERITY_RANK.__getitem__) if known else None


def events_alerts_phrase(events: list[dict] | None, alerts: list[dict] | None) -> str:
    """'1 evento crítico e 1 alerta aberto' / 'nenhum evento e nenhum alerta'."""
    events = events or []
    alerts = alerts or []
    if events:
        top = highest_severity([e.get("severity") for e in events])
        adjective = SEVERITY_ADJECTIVES.get(top, "")
        if len(events) == 1:
            ev = f"1 evento {adjective}".strip()
        else:
            top_label = SEVERITY_LABELS.get(top, "").lower()
            ev = f"{len(events)} eventos" + (f" (maior severidade: {top_label})" if top_label else "")
    else:
        ev = "nenhum evento"
    open_alerts = [a for a in alerts if a.get("status", "open") == "open"]
    if not alerts:
        al = "nenhum alerta"
    elif open_alerts:
        al = plural(len(open_alerts), "alerta aberto", "alertas abertos")
    else:
        al = plural(len(alerts), "alerta")
    return f"{ev} e {al}"
