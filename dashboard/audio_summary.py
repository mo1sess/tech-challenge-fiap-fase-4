"""Resumo legivel da analise de audio para o dashboard (funcoes puras, sem streamlit/requests)."""

from __future__ import annotations

from typing import Any

try:
    from .common_summary import (
        SEVERITY_LABELS,
        _num,
        format_datetime,
        format_decimal,
        format_percent,
        format_seconds,
        patient_label as _patient_label,
    )
except ImportError:  # carregado como modulo de topo pelo Streamlit
    from common_summary import (
        SEVERITY_LABELS,
        _num,
        format_datetime,
        format_decimal,
        format_percent,
        format_seconds,
        patient_label as _patient_label,
    )

SIGNAL_LABELS = {
    "help_request": "Pedido de ajuda",
    "pain_report": "Dor",
    "breathing_report": "Respiração",
}
CONTEXT_LABELS = {
    "affirmed": "Afirmado",
    "negated": "Negado",
    "historical": "Histórico",
    "third_party": "Terceiros",
}
STATUS_LABELS = {
    "completed": "Concluído",
    "failed": "Falhou",
    "pending": "Pendente",
    "processing": "Processando",
}
TRANSCRIPTION_STATUS_LABELS = {
    "recognized": "reconhecida",
    "no_match": "nenhuma fala reconhecida",
}
PROVIDER_LABELS = {
    "faster_whisper": "faster-whisper",
    "azure": "Azure Speech",
    "azure_speech": "Azure Speech",  # valor gravado por azure_speech.py
}

# Mesma regra de app/services/audio_event_flow.py: so achados afirmados geram evento
# (um evento por sinal por job). Usada apenas como fallback quando os eventos reais
# do job nao estao disponiveis.
EVENT_CONTEXT = "affirmed"


def format_provider(transcription: dict | None) -> str:
    transcription = transcription or {}
    provider = transcription.get("provider")
    if not provider:
        return "—"
    label = PROVIDER_LABELS.get(str(provider).lower().replace("-", "_"), str(provider))
    model = transcription.get("model")
    return f"{label} ({model})" if model else label


def _event_signals_for_job(events: list[dict] | None, job_id: str | None) -> set[str] | None:
    if events is None or not job_id:
        return None
    signals = set()
    for event in events:
        payload = event.get("payload") or {}
        if event.get("source") == "audio_analysis" and payload.get("job_id") == job_id:
            if payload.get("signal"):
                signals.add(payload["signal"])
    return signals


def _conclusion(findings: list[dict], event_count: int, alert_count: int, transcription_ok: bool) -> str:
    if not findings:
        return "Nenhum sinal identificado na transcrição."
    n = len(findings)
    achados = f"{n} achado" if n == 1 else f"{n} achados"
    eventos = (
        "nenhum evento de revisão criado"
        if event_count == 0
        else f"{event_count} evento de revisão criado"
        if event_count == 1
        else f"{event_count} eventos de revisão criados"
    )
    alertas = (
        "nenhum alerta (o áudio não gera alerta automático)"
        if alert_count == 0
        else f"{alert_count} alerta" + ("s" if alert_count > 1 else "")
    )
    return f"{achados}, {eventos}, {alertas}"


def build_audio_summary(job: dict, events: list[dict] | None = None, patients: list[dict] | None = None) -> dict:
    """Monta o resumo legivel de um job de analise de audio.

    Se `events` for informado, "Gerou evento?" vem dos eventos reais do job
    (source audio_analysis, payload.job_id == job.id, casando por payload.signal);
    caso contrario deriva do contexto do achado (afirmado => sim).
    """
    job = job or {}
    result = job.get("result") or {}
    analysis = result.get("analysis") or {}
    transcription = analysis.get("transcription") or {}
    acoustic = analysis.get("acoustic") or {}
    text_analysis = analysis.get("text_analysis") or {}
    raw_findings = text_analysis.get("findings") or []

    event_ids = result.get("event_ids") or []
    alert_ids = result.get("alert_ids") or []

    event_signals = _event_signals_for_job(events, job.get("id"))
    findings = []
    for item in raw_findings:
        signal = item.get("signal")
        context = item.get("context")
        if event_signals is not None:
            generated = signal in event_signals
        else:
            generated = context == EVENT_CONTEXT and bool(event_ids)
        findings.append(
            {
                "Sinal": SIGNAL_LABELS.get(signal, str(signal or "—")),
                "Expressão": item.get("expression") or "—",
                "Contexto": CONTEXT_LABELS.get(context, str(context or "—")),
                "Gerou evento?": "Sim" if generated else "Não",
                "Trecho": item.get("evidence") or "—",
            }
        )

    text = (transcription.get("text") or "").strip()
    t_status = transcription.get("status")
    if text:
        transcription_text, transcription_warning = text, None
    elif t_status == "no_match":
        transcription_text, transcription_warning = "", "Nenhuma fala foi reconhecida neste áudio."
    elif not transcription:
        transcription_text, transcription_warning = "", "Transcrição indisponível para este job."
    else:
        transcription_text, transcription_warning = "", "A transcrição veio vazia."

    if event_signals is not None:
        event_count = len(event_signals)
    else:
        event_count = len(event_ids)

    status = job.get("status")
    return {
        "job_id": job.get("id"),
        "status": STATUS_LABELS.get(status, str(status or "—")),
        "status_raw": status,
        "error": job.get("error"),
        "provider": format_provider(transcription),
        "patient": _patient_label(job.get("patient_id"), patients),
        "created_at": format_datetime(job.get("created_at")),
        "transcription_text": transcription_text,
        "transcription_warning": transcription_warning,
        "metrics": {
            "Duração": format_seconds(acoustic.get("duration_seconds")),
            "Silêncio": format_percent(acoustic.get("silence_ratio")),
            "RMS": format_decimal(acoustic.get("rms")),
            "Pico": format_decimal(acoustic.get("peak_amplitude")),
            "Clipping": format_percent(acoustic.get("clipping_ratio")),
        },
        "findings": findings,
        "event_count": event_count,
        "alert_count": len(alert_ids),
        "conclusion": _conclusion(findings, event_count, len(alert_ids), bool(text)),
        "disclaimer": analysis.get("disclaimer"),
    }


def audio_jobs_options(jobs: list[dict] | None, patients: list[dict] | None = None) -> list[tuple[str, str]]:
    """Lista (rotulo, job_id) de jobs de audio concluidos, mais recentes primeiro."""
    selected = [
        j for j in (jobs or []) if j.get("job_type") == "audio_analysis" and j.get("status") == "completed"
    ]
    selected.sort(key=lambda j: j.get("created_at") or "", reverse=True)
    options = []
    for job in selected:
        parts = [_patient_label(job.get("patient_id"), patients)]
        filename = job.get("filename") or (job.get("media") or {}).get("filename")
        if filename:
            parts.append(str(filename))
        parts.append(format_datetime(job.get("created_at")))
        options.append((" · ".join(parts), job["id"]))
    return options


def compact_audio_events(events: list[dict] | None, patients: list[dict] | None = None) -> list[dict]:
    """Linhas compactas (quando, paciente, tipo, severidade, titulo) dos eventos de audio."""
    rows = []
    for event in events or []:
        if event.get("source") != "audio_analysis":
            continue
        payload = event.get("payload") or {}
        rows.append(
            {
                "Quando": format_datetime(event.get("occurred_at") or event.get("created_at")),
                "Paciente": _patient_label(event.get("patient_id"), patients),
                "Tipo": SIGNAL_LABELS.get(payload.get("signal"), str(event.get("event_type") or "—")),
                "Severidade": SEVERITY_LABELS.get(event.get("severity"), str(event.get("severity") or "—")),
                "Título": event.get("title") or "—",
            }
        )
    return rows
