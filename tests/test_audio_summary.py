"""Testes do resumo legivel de audio (dashboard/audio_summary.py): funcoes puras, sem Streamlit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.audio_summary import (  # noqa: E402
    audio_jobs_options,
    build_audio_summary,
    compact_audio_events,
)


def _job(job_id="job-1", status="completed", transcription=None, acoustic=None, findings=None, **extra):
    analysis = {}
    if transcription is not None:
        analysis["transcription"] = transcription
    if acoustic is not None:
        analysis["acoustic"] = acoustic
    if findings is not None:
        analysis["text_analysis"] = {"findings": findings}
    result = {"analysis": analysis} if analysis else {}
    job = {
        "id": job_id,
        "job_type": "audio_analysis",
        "status": status,
        "patient_id": "pat-1",
        "created_at": "2026-11-23T12:06:54.79Z",
        "result": result,
    }
    job.update(extra)
    return job


PATIENTS = [{"id": "pat-1", "code": "MG-001"}]


def _finding(signal, context, expression="dor no peito", evidence="trecho"):
    return {"signal": signal, "context": context, "expression": expression, "evidence": evidence}


# ---------- Caso 1: rotulo do transcritor ----------


def test_provider_faster_whisper_base_label():
    job = _job(transcription={"provider": "faster_whisper", "model": "base", "status": "recognized", "text": "oi"})
    summary = build_audio_summary(job)
    assert summary["provider"] == "faster-whisper (base)"


def test_provider_azure_speech_label():
    # Provedor real gravado pelo azure_speech.py e "azure_speech"; o rotulo esperado e "Azure Speech".
    job = _job(transcription={"provider": "azure_speech", "status": "recognized", "text": "oi"})
    summary = build_audio_summary(job)
    assert summary["provider"] == "Azure Speech"


def test_provider_missing_transcription_shows_dash():
    summary = build_audio_summary(_job(status="failed"))
    assert summary["provider"] == "—"


# ---------- Caso 2: metricas em pt-BR ----------


def test_metrics_formatted_pt_br():
    job = _job(
        transcription={"provider": "faster_whisper", "model": "base", "status": "recognized", "text": "oi"},
        acoustic={
            "duration_seconds": 8.164,
            "silence_ratio": 0.256098,
            "clipping_ratio": 0.0,
            "rms": 0.067,
            "peak_amplitude": 0.602,
        },
    )
    metrics = build_audio_summary(job)["metrics"]
    assert metrics["Duração"] == "8,2 s"
    assert metrics["Silêncio"] == "25,6 %"
    assert metrics["Clipping"] == "0,0 %"
    assert metrics["RMS"] == "0,067"
    assert metrics["Pico"] == "0,602"


def test_metrics_missing_acoustic_show_dash():
    metrics = build_audio_summary(_job(status="failed"))["metrics"]
    assert metrics == {
        "Duração": "—",
        "Silêncio": "—",
        "RMS": "—",
        "Pico": "—",
        "Clipping": "—",
    }


# ---------- Caso 3: rotulos de achados ----------


def test_findings_labels_and_evidence_preserved():
    job = _job(
        transcription={"provider": "faster_whisper", "model": "base", "status": "recognized", "text": "x"},
        findings=[
            _finding("help_request", "affirmed", "preciso de ajuda", "preciso de ajuda"),
            _finding("pain_report", "negated", "dor", "não sinto dor"),
            _finding("breathing_report", "historical", "falta de ar", "tive falta de ar antes"),
            _finding("pain_report", "third_party", "dor", "meu pai sente dor"),
        ],
    )
    findings = build_audio_summary(job)["findings"]
    assert [f["Sinal"] for f in findings] == ["Pedido de ajuda", "Dor", "Respiração", "Dor"]
    assert [f["Contexto"] for f in findings] == ["Afirmado", "Negado", "Histórico", "Terceiros"]
    assert [f["Trecho"] for f in findings] == [
        "preciso de ajuda",
        "não sinto dor",
        "tive falta de ar antes",
        "meu pai sente dor",
    ]
    assert findings[0]["Expressão"] == "preciso de ajuda"


def test_finding_missing_evidence_shows_dash():
    job = _job(findings=[{"signal": "help_request", "context": "affirmed"}])
    finding = build_audio_summary(job)["findings"][0]
    assert finding["Trecho"] == "—"
    assert finding["Expressão"] == "—"


# ---------- Caso 4: "Gerou evento?" com eventos reais ----------


def test_generated_event_flag_uses_real_events():
    job = _job(
        findings=[
            _finding("help_request", "affirmed"),
            _finding("pain_report", "affirmed"),
        ],
    )
    events = [
        {
            "source": "audio_analysis",
            "event_type": "audio_help_request",
            "payload": {"job_id": "job-1", "signal": "help_request"},
        },
    ]
    findings = build_audio_summary(job, events=events)["findings"]
    assert findings[0]["Sinal"] == "Pedido de ajuda"
    assert findings[0]["Gerou evento?"] == "Sim"
    assert findings[1]["Sinal"] == "Dor"
    assert findings[1]["Gerou evento?"] == "Não"


def test_generated_event_ignores_events_of_other_jobs_or_sources():
    job = _job(findings=[_finding("help_request", "affirmed")])
    events = [
        {"source": "audio_analysis", "payload": {"job_id": "outro-job", "signal": "help_request"}},
        {"source": "vital_sign", "payload": {"job_id": "job-1", "signal": "help_request"}},
    ]
    summary = build_audio_summary(job, events=events)
    assert summary["findings"][0]["Gerou evento?"] == "Não"
    assert summary["event_count"] == 0


# ---------- Caso 5: fallback sem events ----------


def test_generated_event_fallback_affirmed_with_event_ids_is_yes():
    job = _job(findings=[_finding("help_request", "affirmed")])
    job["result"]["event_ids"] = ["evt-1"]
    assert build_audio_summary(job)["findings"][0]["Gerou evento?"] == "Sim"


def test_generated_event_fallback_without_event_ids_is_no():
    job = _job(findings=[_finding("help_request", "affirmed")])
    job["result"]["event_ids"] = []
    assert build_audio_summary(job)["findings"][0]["Gerou evento?"] == "Não"


def test_generated_event_fallback_negated_with_event_ids_is_no():
    job = _job(findings=[_finding("help_request", "negated")])
    job["result"]["event_ids"] = ["evt-1"]
    assert build_audio_summary(job)["findings"][0]["Gerou evento?"] == "Não"


# ---------- Caso 6: conclusao ----------


def test_conclusion_counts_findings_events_and_no_alert():
    job = _job(
        findings=[
            _finding("help_request", "affirmed"),
            _finding("pain_report", "affirmed"),
            _finding("breathing_report", "negated"),
        ],
    )
    job["result"]["event_ids"] = ["evt-1", "evt-2"]
    events = [
        {"source": "audio_analysis", "payload": {"job_id": "job-1", "signal": "help_request"}},
        {"source": "audio_analysis", "payload": {"job_id": "job-1", "signal": "pain_report"}},
    ]
    conclusion = build_audio_summary(job, events=events)["conclusion"]
    assert "3 achados" in conclusion
    assert "2 eventos" in conclusion
    assert "nenhum alerta" in conclusion


def test_conclusion_zero_findings():
    job = _job(findings=[])
    summary = build_audio_summary(job)
    assert summary["conclusion"] == "Nenhum sinal identificado na transcrição."
    assert summary["findings"] == []


# ---------- Caso 7: transcricao vazia / no_match ----------


def test_no_match_transcription_warns_without_exception():
    job = _job(transcription={"provider": "faster_whisper", "model": "base", "status": "no_match", "text": ""})
    summary = build_audio_summary(job)
    assert summary["transcription_text"] == ""
    assert summary["transcription_warning"] == "Nenhuma fala foi reconhecida neste áudio."


def test_empty_recognized_transcription_warns_without_exception():
    job = _job(transcription={"provider": "faster_whisper", "model": "base", "status": "recognized", "text": "   "})
    summary = build_audio_summary(job)
    assert summary["transcription_text"] == ""
    assert summary["transcription_warning"] == "A transcrição veio vazia."


def test_transcription_with_text_has_no_warning():
    job = _job(transcription={"provider": "faster_whisper", "model": "base", "status": "recognized", "text": "oi"})
    summary = build_audio_summary(job)
    assert summary["transcription_text"] == "oi"
    assert summary["transcription_warning"] is None


def test_missing_transcription_warns_unavailable():
    summary = build_audio_summary(_job(status="failed"))
    assert summary["transcription_text"] == ""
    assert summary["transcription_warning"] == "Transcrição indisponível para este job."


# ---------- Caso 8: job falho sem result.analysis ----------


def test_failed_job_without_analysis_does_not_raise():
    job = {
        "id": "job-f",
        "job_type": "audio_analysis",
        "status": "failed",
        "error": "credenciais ausentes",
        "patient_id": "pat-1",
        "created_at": "2026-11-23T12:06:54Z",
        "result": None,
    }
    summary = build_audio_summary(job, events=[], patients=PATIENTS)
    assert summary["status"] == "Falhou"
    assert summary["status_raw"] == "failed"
    assert summary["error"] == "credenciais ausentes"
    assert summary["findings"] == []
    assert summary["event_count"] == 0
    assert summary["alert_count"] == 0


def test_failed_job_without_result_key_does_not_raise():
    job = {"id": "job-g", "status": "failed"}
    summary = build_audio_summary(job)
    assert summary["status"] == "Falhou"
    assert summary["job_id"] == "job-g"


def test_none_job_does_not_raise():
    summary = build_audio_summary(None)
    assert summary["job_id"] is None
    assert summary["findings"] == []


# ---------- Caso 9: opcoes da lista de jobs ----------


def test_audio_jobs_options_filters_and_orders_newest_first():
    jobs = [
        {
            "id": "vid-1",
            "job_type": "video_analysis",
            "status": "completed",
            "patient_id": "pat-1",
            "created_at": "2026-11-24T10:00:00Z",
        },
        {
            "id": "aud-queued",
            "job_type": "audio_analysis",
            "status": "queued",
            "patient_id": "pat-1",
            "created_at": "2026-11-24T09:00:00Z",
        },
        {
            "id": "aud-old",
            "job_type": "audio_analysis",
            "status": "completed",
            "patient_id": "pat-1",
            "created_at": "2026-11-22T08:00:00Z",
        },
        {
            "id": "aud-new",
            "job_type": "audio_analysis",
            "status": "completed",
            "patient_id": "pat-1",
            "created_at": "2026-11-23T12:06:54Z",
        },
    ]
    options = audio_jobs_options(jobs, patients=PATIENTS)
    assert [job_id for _, job_id in options] == ["aud-new", "aud-old"]
    assert all("MG-001" in label for label, _ in options)


def test_audio_jobs_options_label_without_patients_uses_fallback():
    jobs = [
        {
            "id": "aud-1",
            "job_type": "audio_analysis",
            "status": "completed",
            "patient_id": "abcdef1234567890",
            "created_at": "2026-11-23T12:06:54Z",
        },
    ]
    options = audio_jobs_options(jobs)
    assert options[0][1] == "aud-1"
    assert "abcdef12" in options[0][0]


def test_audio_jobs_options_empty_input():
    assert audio_jobs_options([]) == []
    assert audio_jobs_options(None) == []


# ---------- Caso 10: eventos compactos ----------


def test_compact_audio_events_filters_source_and_keeps_documented_columns():
    events = [
        {
            "source": "audio_analysis",
            "event_type": "audio_help_request",
            "severity": "low",
            "title": "Pedido de ajuda detectado",
            "occurred_at": "2026-11-23T12:06:54Z",
            "patient_id": "pat-1",
            "payload": {"job_id": "job-1", "signal": "help_request"},
        },
        {
            "source": "vital_sign",
            "event_type": "vital_critical",
            "severity": "critical",
            "title": "FC alta",
            "occurred_at": "2026-11-23T12:10:00Z",
            "patient_id": "pat-1",
            "payload": {},
        },
    ]
    rows = compact_audio_events(events, patients=PATIENTS)
    assert len(rows) == 1
    row = rows[0]
    assert set(row.keys()) == {"Quando", "Paciente", "Tipo", "Severidade", "Título"}
    assert row["Quando"] == "23/11/2026 12:06"
    assert row["Paciente"] == "MG-001"
    assert row["Tipo"] == "Pedido de ajuda"
    assert row["Severidade"] == "Baixa"
    assert row["Título"] == "Pedido de ajuda detectado"


def test_compact_audio_events_empty_input():
    assert compact_audio_events(None) == []
    assert compact_audio_events([]) == []
