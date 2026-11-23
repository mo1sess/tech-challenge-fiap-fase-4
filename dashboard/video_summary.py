"""Resumo legivel da analise de video para o dashboard (funcoes puras)."""

from __future__ import annotations

try:
    from .common_summary import (
        format_datetime,
        format_number,
        format_percent_points,
        format_seconds,
        job_status_label,
        patient_label,
        plural,
        severity_label,
    )
except ImportError:  # carregado como modulo de topo pelo Streamlit
    from common_summary import (
        format_datetime,
        format_number,
        format_percent_points,
        format_seconds,
        job_status_label,
        patient_label,
        plural,
        severity_label,
    )

# Valores de VideoAnalysis.activity_label (app/modules/video/processor.py).
ACTIVITY_LABELS = {
    "very_low_motion": "Movimento muito baixo",
    "high_motion": "Movimento alto",
    "expected_demo_range": "Dentro da faixa esperada da demonstração",
}
# Codigos de VideoAnomaly.code.
RULE_LABELS = {
    "sustained_low_motion": "Baixo movimento prolongado",
    "abrupt_visual_change": "Mudança visual brusca",
}
VIDEO_SOURCE = "video_analysis"


def _percent(value) -> str:
    # valores pequenos (0,0671 %) precisam de mais casas para nao virar "0,1 %"
    return format_percent_points(value, 2 if isinstance(value, (int, float)) and abs(value) < 1 else 1)


def _anomaly_rows(anomalies: list[dict]) -> list[dict]:
    rows = []
    for item in anomalies:
        code = item.get("code")
        rows.append(
            {
                "Regra": RULE_LABELS.get(code, str(code or "—")),
                "Observado": _percent(item.get("observed_value")),
                "Limite": _percent(item.get("threshold")),
                "Severidade": severity_label(item.get("severity")),
            }
        )
    return rows


def _conclusion(anomalies: list[dict], event_count: int, alert_count: int, has_analysis: bool) -> str:
    if not has_analysis:
        return "Análise indisponível para este job."
    if not anomalies:
        return "Nenhuma anomalia visual detectada."
    if event_count == 0:
        eventos = "nenhum evento de revisão criado"
    elif event_count == 1:
        eventos = "1 evento de revisão criado"
    else:
        eventos = f"{event_count} eventos de revisão criados"
    alertas = "nenhum alerta" if alert_count == 0 else plural(alert_count, "alerta")
    return f"{plural(len(anomalies), 'anomalia detectada', 'anomalias detectadas')}, {eventos}, {alertas}."


def build_video_summary(job: dict | None, patients: list[dict] | None = None) -> dict:
    """Resume um job de video (item de /jobs, GET /jobs/{id} ou `job` de um process/demo).

    Retorno: {"job_id", "status", "status_raw", "error", "patient", "created_at",
    "metrics": {"Quadros analisados", "Duração", "FPS", "Movimento médio", "Pico de movimento",
    "Atividade"}, "anomalies": [{Regra, Observado, Limite, Severidade}], "event_count",
    "alert_count", "conclusion", "disclaimer"}.
    """
    job = job or {}
    result = job.get("result") or {}
    analysis = result.get("analysis") or {}
    anomalies = analysis.get("anomalies") or []
    event_count = len(result.get("event_ids") or [])
    alert_count = len(result.get("alert_ids") or [])

    analyzed = analysis.get("analyzed_frame_count")
    total = analysis.get("source_frame_count")
    if isinstance(analyzed, (int, float)) and isinstance(total, (int, float)):
        frames = f"{format_number(analyzed)} de {format_number(total)}"
    else:
        frames = format_number(analyzed)
    fps = analysis.get("fps")
    return {
        "job_id": job.get("id"),
        "status": job_status_label(job.get("status")),
        "status_raw": job.get("status"),
        "error": job.get("error"),
        "patient": patient_label(job.get("patient_id"), patients),
        "created_at": format_datetime(job.get("created_at")),
        "metrics": {
            "Quadros analisados": frames,
            "Duração": format_seconds(analysis.get("duration_seconds")),
            "FPS": format_number(fps, 1) if isinstance(fps, (int, float)) else "—",
            "Movimento médio": _percent(analysis.get("mean_motion_percent")),
            "Pico de movimento": _percent(analysis.get("peak_motion_percent")),
            "Atividade": ACTIVITY_LABELS.get(analysis.get("activity_label"), str(analysis.get("activity_label") or "—")),
        },
        "anomalies": _anomaly_rows(anomalies),
        "event_count": event_count,
        "alert_count": alert_count,
        "conclusion": _conclusion(anomalies, event_count, alert_count, bool(analysis)),
        "disclaimer": analysis.get("disclaimer"),
    }


def video_jobs_options(jobs: list[dict] | None, patients: list[dict] | None = None) -> list[tuple[str, str]]:
    """Lista (rotulo, job_id) de jobs de video concluidos, mais recentes primeiro."""
    selected = [j for j in (jobs or []) if j.get("job_type") == "video_analysis" and j.get("status") == "completed"]
    selected.sort(key=lambda j: j.get("created_at") or "", reverse=True)
    return [
        (f"{patient_label(j.get('patient_id'), patients)} · {format_datetime(j.get('created_at'))}", j["id"])
        for j in selected
    ]


def compact_video_events(events: list[dict] | None, patients: list[dict] | None = None) -> list[dict]:
    """Linhas: Quando, Paciente, Regra, Severidade, Observado, Limite."""
    rows = []
    for event in events or []:
        if event.get("source") != VIDEO_SOURCE:
            continue
        payload = event.get("payload") or {}
        code = event.get("event_type")
        rows.append(
            {
                "Quando": format_datetime(event.get("occurred_at") or event.get("created_at")),
                "Paciente": patient_label(event.get("patient_id"), patients),
                "Regra": RULE_LABELS.get(code, str(code or "—")),
                "Severidade": severity_label(event.get("severity")),
                "Observado": _percent(payload.get("observed_value")),
                "Limite": _percent(payload.get("threshold")),
            }
        )
    return rows
