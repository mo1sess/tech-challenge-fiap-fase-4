"""Testes dos helpers comuns dos resumos do dashboard (dashboard/common_summary.py): funcoes puras, sem Streamlit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.common_summary import (  # noqa: E402
    events_alerts_phrase,
    format_bytes,
    format_datetime,
    format_decimal,
    format_number,
    format_percent,
    format_percent_points,
    format_seconds,
    highest_severity,
    job_status_label,
    patient_label,
    severity_label,
    short_hash,
)


# ---------- Formatacao pt-BR de numeros ----------


def test_format_number_uses_decimal_comma():
    assert format_number(1234.5) == "1234,5"
    assert format_number(0.5, 2) == "0,50"


def test_format_number_integer_has_no_decimals():
    assert format_number(148.0) == "148"
    assert format_number(7) == "7"


def test_format_decimal_three_places_with_comma():
    assert format_decimal(0.0671) == "0,067"


def test_format_number_missing_value_returns_dash_without_raising():
    assert format_number(None) == "—"
    assert format_number("abc") == "—"
    assert format_number(True) == "—"  # bool nao e numero para o resumo


def test_format_decimal_invalid_value_returns_dash():
    assert format_decimal(None) == "—"
    assert format_decimal("x") == "—"


# ---------- Tamanho (bytes -> KB/MB) ----------


def test_format_bytes_below_one_kilobyte_stays_in_bytes():
    assert format_bytes(512) == "512 B"


def test_format_bytes_converts_to_kilobytes_with_decimal_comma():
    assert format_bytes(186100) == "181,7 KB"


def test_format_bytes_converts_to_megabytes():
    assert format_bytes(2 * 1024 * 1024) == "2,0 MB"


def test_format_bytes_missing_or_negative_returns_dash():
    assert format_bytes(None) == "—"
    assert format_bytes(-1) == "—"
    assert format_bytes("grande") == "—"


# ---------- Data ISO ----------


def test_format_datetime_iso_utc_to_dd_mm_yyyy_hh_mm():
    # Formato real: dd/mm/aaaa hh:mm, sem conversao de fuso (UTC mantido).
    assert format_datetime("2026-11-23T12:06:54.79Z") == "23/11/2026 12:06"


def test_format_datetime_invalid_or_missing_returns_dash():
    assert format_datetime(None) == "—"
    assert format_datetime("abc") == "—"
    assert format_datetime(12345) == "—"


# ---------- Segundos, percentuais e hash ----------


def test_format_seconds_and_percent_helpers():
    assert format_seconds(8.164) == "8,2 s"
    assert format_seconds(None) == "—"
    assert format_percent(0.256) == "25,6 %"  # recebe razao 0..1
    assert format_percent_points(0.0671, 2) == "0,07 %"  # ja em pontos percentuais
    assert format_percent_points(None) == "—"


def test_short_hash_keeps_first_twelve_chars():
    sha = "a1b2c3d4e5f6" + "0" * 52
    assert short_hash(sha, 12) == "a1b2c3d4e5f6"
    assert len(short_hash(sha, 12)) == 12
    assert short_hash(None) == "—"


# ---------- Rotulos de severidade e status ----------


def test_severity_labels_map_to_pt_br():
    assert severity_label("low") == "Baixa"
    assert severity_label("medium") == "Média"
    assert severity_label("high") == "Alta"
    assert severity_label("critical") == "Crítica"


def test_severity_unknown_or_missing_does_not_raise():
    assert severity_label("desconhecida") == "desconhecida"
    assert severity_label(None) == "—"


def test_job_status_labels_map_to_pt_br():
    assert job_status_label("queued") == "Na fila"
    assert job_status_label("processing") == "Processando"
    assert job_status_label("completed") == "Concluído"
    assert job_status_label("failed") == "Falhou"


def test_job_status_unknown_or_missing_does_not_raise():
    assert job_status_label("arquivado") == "arquivado"
    assert job_status_label(None) == "—"


# ---------- Rotulo de paciente e severidade maxima ----------


def test_patient_label_prefers_code_and_falls_back_to_id():
    patients = [{"id": "pat-1", "code": "MG-001"}]
    assert patient_label("pat-1", patients) == "MG-001"
    assert patient_label("pat-9", patients) == "pat-9"
    assert patient_label(None, None) == "—"


def test_highest_severity_ignores_unknown_values():
    assert highest_severity(["low", "desconhecida", "medium"]) == "medium"
    assert highest_severity([]) is None


# ---------- Frase de eventos e alertas ----------


def test_events_alerts_phrase_single_critical_event_and_open_alert():
    phrase = events_alerts_phrase(
        [{"severity": "critical"}],
        [{"severity": "critical", "status": "open"}],
    )
    assert phrase == "1 evento crítico e 1 alerta aberto"


def test_events_alerts_phrase_single_high_event_uses_severity_adjective():
    phrase = events_alerts_phrase([{"severity": "high"}], [{"status": "open"}])
    assert phrase == "1 evento de severidade alta e 1 alerta aberto"


def test_events_alerts_phrase_several_events_shows_top_severity():
    phrase = events_alerts_phrase(
        [{"severity": "high"}, {"severity": "critical"}],
        [{"status": "open"}, {"status": "open"}],
    )
    assert phrase == "2 eventos (maior severidade: crítica) e 2 alertas abertos"


def test_events_alerts_phrase_empty_lists():
    assert events_alerts_phrase([], []) == "nenhum evento e nenhum alerta"
    assert events_alerts_phrase(None, None) == "nenhum evento e nenhum alerta"


def test_events_alerts_phrase_only_resolved_alerts_are_not_open():
    phrase = events_alerts_phrase([], [{"status": "resolved"}])
    assert phrase == "nenhum evento e 1 alerta"
