"""Testes do resumo de midia e jobs (dashboard/media_summary.py): funcoes puras, sem Streamlit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.media_summary import build_upload_summary, compact_jobs  # noqa: E402

PATIENTS = [{"id": "pat-1", "code": "MG-001"}]
SHA256 = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


def _upload(kind="audio", filename="fala.wav", job_status="completed", components=None):
    job_type = "audio_analysis" if kind == "audio" else "video_analysis"
    pipeline = {"components": components} if components is not None else None
    result = {"pipeline": pipeline} if pipeline else {}
    return {
        "media": {
            "id": "med-1",
            "patient_id": "pat-1",
            "kind": kind,
            "original_filename": filename,
            "content_type": "audio/wav" if kind == "audio" else "video/x-msvideo",
            "sha256": SHA256,
            "size_bytes": 186100,
            "is_synthetic": True,
            "created_at": "2026-11-23T12:06:54Z",
        },
        "job": {
            "id": "job-1",
            "patient_id": "pat-1",
            "media_file_id": "med-1",
            "job_type": job_type,
            "status": job_status,
            "progress": 100.0,
            "result": result,
            "error": None,
            "created_at": "2026-11-23T12:06:54Z",
            "updated_at": "2026-11-23T12:07:10Z",
        },
        "note": "Upload sintetico registrado.",
    }


# ---------- Resposta de upload ----------


def test_upload_summary_formats_size_hash_status_and_patient():
    summary = build_upload_summary(
        _upload(components=["faster_whisper_local", "numpy_pcm_wav", "deterministic_context_rules_v2"]),
        PATIENTS,
    )
    assert summary["filename"] == "fala.wav"
    assert summary["kind"] == "Áudio"
    assert summary["size"] == "181,7 KB"
    assert summary["sha256"] == SHA256[:12]
    assert len(summary["sha256"]) == 12
    assert summary["job_status"] == "Concluído"
    assert summary["job_status_raw"] == "completed"
    assert summary["progress"] == "100 %"
    assert summary["patient"] == "MG-001"


def test_upload_summary_lists_pipeline_steps_in_pt_br():
    summary = build_upload_summary(
        _upload(components=["faster_whisper_local", "numpy_pcm_wav", "deterministic_context_rules_v2"]),
        PATIENTS,
    )
    assert summary["steps"] == [
        "Transcrição local (faster-whisper)",
        "Métricas acústicas (WAV PCM)",
        "Análise textual por regras de contexto",
    ]


def test_upload_summary_unknown_pipeline_component_keeps_raw_name():
    summary = build_upload_summary(_upload(components=["componente_novo"]), PATIENTS)
    assert summary["steps"] == ["componente_novo"]


def test_upload_summary_video_kind_and_queued_status():
    summary = build_upload_summary(_upload(kind="video", filename="corredor.avi", job_status="queued"), PATIENTS)
    assert summary["kind"] == "Vídeo"
    assert summary["job_status"] == "Na fila"
    assert summary["steps"] == []


def test_upload_summary_missing_fields_do_not_raise():
    summary = build_upload_summary({}, None)
    assert summary["filename"] == "—"
    assert summary["sha256"] == "—"
    assert summary["size"] == "—"
    assert summary["steps"] == []


# ---------- Tabela de jobs ----------


def test_compact_jobs_translates_type_and_status_and_keeps_error():
    jobs = [
        {
            "id": "job-a",
            "patient_id": "pat-1",
            "job_type": "audio_analysis",
            "status": "completed",
            "progress": 100.0,
            "error": None,
            "created_at": "2026-11-23T12:06:54Z",
        },
        {
            "id": "job-v",
            "patient_id": "pat-1",
            "job_type": "video_analysis",
            "status": "failed",
            "progress": 100.0,
            "error": "Não foi possível abrir o vídeo",
            "created_at": "2026-11-23T12:10:00Z",
        },
    ]
    rows = compact_jobs(jobs, PATIENTS)
    assert set(rows[0]) == {"Tipo", "Paciente", "Status", "Progresso", "Criado em", "Erro"}
    assert rows[0] == {
        "Tipo": "Áudio",
        "Paciente": "MG-001",
        "Status": "Concluído",
        "Progresso": "100 %",
        "Criado em": "23/11/2026 12:06",
        "Erro": "—",
    }
    assert rows[1]["Tipo"] == "Vídeo"
    assert rows[1]["Status"] == "Falhou"
    assert rows[1]["Erro"] == "Não foi possível abrir o vídeo"


def test_compact_jobs_empty_or_none_returns_empty_list():
    assert compact_jobs([], PATIENTS) == []
    assert compact_jobs(None) == []
