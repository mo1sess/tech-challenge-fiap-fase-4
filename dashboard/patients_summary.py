"""Resumo legivel da aba Pacientes ficticios (funcoes puras)."""

from __future__ import annotations

try:
    from .common_summary import format_datetime
except ImportError:  # carregado como modulo de topo pelo Streamlit
    from common_summary import format_datetime


def compact_patients(patients: list[dict] | None) -> list[dict]:
    """Linhas: Código, Nome (alias), Ano de nascimento, Sintético, Cadastrado em."""
    rows = []
    for patient in patients or []:
        birth_year = patient.get("birth_year")
        rows.append(
            {
                "Código": patient.get("code") or "—",
                "Nome (alias)": patient.get("alias") or "—",
                "Ano de nascimento": str(birth_year) if birth_year else "—",
                "Sintético": "Sim" if patient.get("is_synthetic") else "Não",
                "Cadastrado em": format_datetime(patient.get("created_at")),
            }
        )
    return rows
