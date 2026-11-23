"""Testes do resumo da aba Pacientes ficticios (dashboard/patients_summary.py): funcoes puras, sem Streamlit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.patients_summary import compact_patients  # noqa: E402

EXPECTED_COLUMNS = {"Código", "Nome (alias)", "Ano de nascimento", "Sintético", "Cadastrado em"}


def _patient(code, alias, birth_year, is_synthetic=True, created_at="2026-11-20T08:30:00Z"):
    return {
        "id": f"id-{code}",
        "code": code,
        "alias": alias,
        "birth_year": birth_year,
        "notes": "observacao interna que nao deve aparecer",
        "is_synthetic": is_synthetic,
        "created_at": created_at,
    }


def test_two_patients_yield_two_rows_with_only_documented_columns():
    rows = compact_patients(
        [
            _patient("MG-001", "Paciente Alfa", 1990),
            _patient("MG-002", "Paciente Beta", 1975),
        ]
    )
    assert len(rows) == 2
    for row in rows:
        assert set(row) == EXPECTED_COLUMNS


def test_patient_row_values_are_formatted_for_display():
    rows = compact_patients([_patient("MG-001", "Paciente Alfa", 1990)])
    assert rows[0] == {
        "Código": "MG-001",
        "Nome (alias)": "Paciente Alfa",
        "Ano de nascimento": "1990",
        "Sintético": "Sim",
        "Cadastrado em": "20/11/2026 08:30",
    }


def test_is_synthetic_true_shows_sim_and_false_shows_nao():
    rows = compact_patients(
        [
            _patient("MG-001", "Paciente Alfa", 1990, is_synthetic=True),
            _patient("MG-002", "Paciente Beta", 1975, is_synthetic=False),
        ]
    )
    assert rows[0]["Sintético"] == "Sim"
    assert rows[1]["Sintético"] == "Não"


def test_missing_birth_year_and_created_at_show_dash():
    rows = compact_patients([_patient("MG-003", "Paciente Gama", None, created_at=None)])
    assert rows[0]["Ano de nascimento"] == "—"
    assert rows[0]["Cadastrado em"] == "—"


def test_empty_or_none_input_returns_empty_list():
    assert compact_patients([]) == []
    assert compact_patients(None) == []
