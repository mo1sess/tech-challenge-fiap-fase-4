"""Testes do resumo de analise de video (dashboard/video_summary.py): funcoes puras, sem Streamlit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.video_summary import (  # noqa: E402
    build_video_summary,
    compact_video_events,
    video_jobs_options,
)

PATIENTS = [{"id": "pat-1", "code": "MG-001"}]
DISCLAIMER = "Dado sintetico, uso demonstrativo."


def _analysis(anomalies, mean=0.0671, peak=0.2, activity="very_low_motion"):
    return {
        "decoder": "opencv",
        "width": 640,
        "height": 480,
        "fps": 10.0,
        "duration_seconds": 2.0,
        "source_frame_count": 20,
        "analyzed_frame_count": 7,
        "sample_every_n_frames": 3,
        "mean_motion_percent": mean,
        "peak_motion_percent": peak,
        "activity_label": activity,
        "anomalies": anomalies,
        "disclaimer": DISCLAIMER,
    }


def _low_motion_anomaly():
    return {
        "code": "sustained_low_motion",
        "severity": "high",
        "title": "Baixo movimento prolongado",
        "description": "Movimento medio abaixo do limite.",
        "observed_value": 0.0671,
        "threshold": 0.35,
        "unit": "percent_changed_pixels",
    }


def _abrupt_anomaly():
    return {
        "code": "abrupt_visual_change",
        "severity": "high",
        "title": "Mudança visual brusca",
        "description": "Pico de movimento acima do limite.",
        "observed_value": 94.3681,
        "threshold": 20.0,
        "unit": "percent_changed_pixels",
    }


def _completed_job(analysis, event_ids=("ev-1",), alert_ids=("al-1",), job_id="job-v1", created_at="2026-11-23T12:10:00Z"):
    return {
        "id": job_id,
        "patient_id": "pat-1",
        "job_type": "video_analysis",
        "status": "completed",
        "progress": 100.0,
        "error": None,
        "created_at": created_at,
        "result": {
            "analysis": analysis,
            "event_ids": list(event_ids),
            "alert_ids": list(alert_ids),
        },
    }


# ---------- Job concluido com anomalia ----------


def test_low_motion_anomaly_uses_pt_br_rule_and_formatted_value_and_limit():
    job = _completed_job(_analysis([_low_motion_anomaly()], mean=0.0671, activity="very_low_motion"))
    summary = build_video_summary(job, PATIENTS)
    assert summary["anomalies"] == [
        {
            "Regra": "Baixo movimento prolongado",
            "Observado": "0,07 %",
            "Limite": "0,35 %",
            "Severidade": "Alta",
        }
    ]


def test_abrupt_change_anomaly_uses_pt_br_rule_and_formatted_value_and_limit():
    job = _completed_job(_analysis([_abrupt_anomaly()], mean=3.2, peak=94.3681, activity="high_motion"))
    summary = build_video_summary(job, PATIENTS)
    assert summary["anomalies"] == [
        {
            "Regra": "Mudança visual brusca",
            "Observado": "94,4 %",
            "Limite": "20,0 %",
            "Severidade": "Alta",
        }
    ]


def test_anomalous_job_conclusion_counts_one_event_and_one_alert():
    job = _completed_job(_analysis([_low_motion_anomaly()]))
    summary = build_video_summary(job, PATIENTS)
    assert summary["event_count"] == 1
    assert summary["alert_count"] == 1
    assert summary["conclusion"] == "1 anomalia detectada, 1 evento de revisão criado, 1 alerta."


def test_video_summary_header_fields_and_metrics():
    job = _completed_job(_analysis([_low_motion_anomaly()], mean=0.0671, peak=0.2))
    summary = build_video_summary(job, PATIENTS)
    assert summary["job_id"] == "job-v1"
    assert summary["status"] == "Concluído"
    assert summary["patient"] == "MG-001"
    assert summary["created_at"] == "23/11/2026 12:10"
    assert summary["metrics"] == {
        "Quadros analisados": "7 de 20",
        "Duração": "2,0 s",
        "FPS": "10,0",
        "Movimento médio": "0,07 %",
        "Pico de movimento": "0,20 %",
        "Atividade": "Movimento muito baixo",
    }
    assert summary["disclaimer"] == DISCLAIMER


# ---------- Job sem anomalias ----------


def test_job_without_anomalies_has_no_anomaly_rows_and_no_anomaly_conclusion():
    job = _completed_job(_analysis([], mean=5.0, peak=8.0, activity="expected_demo_range"), event_ids=(), alert_ids=())
    summary = build_video_summary(job, PATIENTS)
    assert summary["anomalies"] == []
    assert summary["event_count"] == 0
    assert summary["alert_count"] == 0
    assert summary["conclusion"] == "Nenhuma anomalia visual detectada."
    assert summary["metrics"]["Atividade"] == "Dentro da faixa esperada da demonstração"


# ---------- Job failed sem result ----------


def test_failed_job_without_result_does_not_raise():
    job = {
        "id": "job-f",
        "patient_id": "pat-1",
        "job_type": "video_analysis",
        "status": "failed",
        "error": "Não foi possível abrir o vídeo",
        "created_at": "2026-11-23T12:11:00Z",
    }
    summary = build_video_summary(job, PATIENTS)
    assert summary["status"] == "Falhou"
    assert summary["error"] == "Não foi possível abrir o vídeo"
    assert summary["anomalies"] == []
    assert summary["conclusion"] == "Análise indisponível para este job."
    assert summary["metrics"]["Quadros analisados"] == "—"
    assert summary["metrics"]["Duração"] == "—"


def test_failed_job_with_empty_result_does_not_raise():
    job = {"id": "job-f2", "job_type": "video_analysis", "status": "failed", "result": {}}
    summary = build_video_summary(job)
    assert summary["conclusion"] == "Análise indisponível para este job."
    assert summary["patient"] == "—"


def test_build_video_summary_none_does_not_raise():
    summary = build_video_summary(None)
    assert summary["status"] == "—"
    assert summary["conclusion"] == "Análise indisponível para este job."


# ---------- Seletor de jobs ----------


def test_video_jobs_options_only_completed_videos_most_recent_first():
    jobs = [
        _completed_job(_analysis([]), job_id="job-old", created_at="2026-11-23T10:00:00Z"),
        _completed_job(_analysis([]), job_id="job-new", created_at="2026-11-23T12:10:00Z"),
        {"id": "job-fail", "patient_id": "pat-1", "job_type": "video_analysis", "status": "failed",
         "created_at": "2026-11-23T13:00:00Z"},
        {"id": "job-audio", "patient_id": "pat-1", "job_type": "audio_analysis", "status": "completed",
         "created_at": "2026-11-23T14:00:00Z"},
    ]
    options = video_jobs_options(jobs, PATIENTS)
    assert options == [
        ("MG-001 · 23/11/2026 12:10", "job-new"),
        ("MG-001 · 23/11/2026 10:00", "job-old"),
    ]


def test_video_jobs_options_empty_list():
    assert video_jobs_options([], PATIENTS) == []
    assert video_jobs_options(None) == []


# ---------- Eventos compactos ----------


def test_compact_video_events_keeps_only_video_rows_with_documented_columns():
    events = [
        {
            "id": "ev-1",
            "patient_id": "pat-1",
            "source": "video_analysis",
            "event_type": "sustained_low_motion",
            "severity": "high",
            "occurred_at": "2026-11-23T12:10:00Z",
            "payload": {"observed_value": 0.0671, "threshold": 0.35},
        },
        {
            "id": "ev-2",
            "patient_id": "pat-1",
            "source": "vital_signs",
            "event_type": "synthetic_vital_sign_anomaly",
            "severity": "critical",
            "occurred_at": "2026-11-23T12:12:00Z",
            "payload": {},
        },
    ]
    rows = compact_video_events(events, PATIENTS)
    assert len(rows) == 1
    assert set(rows[0]) == {"Quando", "Paciente", "Regra", "Severidade", "Observado", "Limite"}
    assert rows[0] == {
        "Quando": "23/11/2026 12:10",
        "Paciente": "MG-001",
        "Regra": "Baixo movimento prolongado",
        "Severidade": "Alta",
        "Observado": "0,07 %",
        "Limite": "0,35 %",
    }
