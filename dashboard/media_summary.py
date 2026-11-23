"""Resumo legivel de midia e jobs (funcoes puras)."""

from __future__ import annotations

try:
    from .common_summary import (
        JOB_TYPE_LABELS,
        MEDIA_KIND_LABELS,
        format_bytes,
        format_datetime,
        format_number,
        job_status_label,
        patient_label,
        short_hash,
    )
except ImportError:  # carregado como modulo de topo pelo Streamlit
    from common_summary import (
        JOB_TYPE_LABELS,
        MEDIA_KIND_LABELS,
        format_bytes,
        format_datetime,
        format_number,
        job_status_label,
        patient_label,
        short_hash,
    )

# Componentes de pipeline gravados em job.result.pipeline.components.
PIPELINE_STEP_LABELS = {
    "faster_whisper_local": "Transcrição local (faster-whisper)",
    "azure_speech_to_text": "Transcrição (Azure Speech)",
    "deterministic_context_rules_v2": "Análise textual por regras de contexto",
    "numpy_pcm_wav": "Métricas acústicas (WAV PCM)",
    "opencv_frame_reader": "Leitura de quadros (OpenCV)",
    "frame_difference_motion": "Movimento por diferença entre quadros",
    "event_alert_bridge": "Geração de evento e alerta",
}


def pipeline_steps(job: dict | None) -> list[str]:
    components = (((job or {}).get("result") or {}).get("pipeline") or {}).get("components") or []
    return [PIPELINE_STEP_LABELS.get(c, str(c)) for c in components]


def build_upload_summary(upload: dict | None, patients: list[dict] | None = None) -> dict:
    """Resume a resposta de POST /patients/{id}/media ({media, job, note}).

    Retorno: {"filename", "kind": "Áudio"/"Vídeo", "content_type", "size", "sha256",
    "job_status", "job_status_raw", "progress": "0 %", "patient", "steps": [rótulos]}.
    """
    upload = upload or {}
    media = upload.get("media") or {}
    job = upload.get("job") or {}
    return {
        "filename": media.get("original_filename") or "—",
        "kind": MEDIA_KIND_LABELS.get(media.get("kind"), str(media.get("kind") or "—")),
        "content_type": media.get("content_type") or "—",
        "size": format_bytes(media.get("size_bytes")),
        "sha256": short_hash(media.get("sha256"), 12),
        "job_status": job_status_label(job.get("status")),
        "job_status_raw": job.get("status"),
        "progress": f"{format_number(job.get('progress'))} %",
        "patient": patient_label(media.get("patient_id") or job.get("patient_id"), patients),
        "steps": pipeline_steps(job),
    }


def compact_jobs(jobs: list[dict] | None, patients: list[dict] | None = None) -> list[dict]:
    """Linhas: Tipo, Paciente, Status, Progresso, Criado em, Erro."""
    return [
        {
            "Tipo": JOB_TYPE_LABELS.get(j.get("job_type"), str(j.get("job_type") or "—")),
            "Paciente": patient_label(j.get("patient_id"), patients),
            "Status": job_status_label(j.get("status")),
            "Progresso": f"{format_number(j.get('progress'))} %",
            "Criado em": format_datetime(j.get("created_at")),
            "Erro": j.get("error") or "—",
        }
        for j in jobs or []
    ]
