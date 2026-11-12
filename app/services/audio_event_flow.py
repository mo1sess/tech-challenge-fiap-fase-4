
from collections import defaultdict

from sqlalchemy.orm import Session

from app.db.models import ClinicalEvent, Severity

EVENT_TYPES = {
    "help_request": (
        "audio_help_request_review",
        "Solicitação de ajuda identificada em áudio sintético",
    ),
    "pain_report": (
        "audio_pain_report_review",
        "Relato de dor identificado em áudio sintético",
    ),
    "breathing_report": (
        "audio_breathing_report_review",
        "Relato respiratório identificado em áudio sintético",
    ),
}


def create_audio_review_events(
    db: Session,
    *,
    patient_id: str,
    job_id: str,
    media_file_id: str,
    text_analysis: dict,
) -> list[ClinicalEvent]:
    """
    Prepara eventos educacionais para achados afirmativos.

    Um evento por categoria de sinal em cada job.
    Nao executa commit: a transacao pertence ao audio_flow.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)

    for finding in text_analysis.get("findings", []):
        signal = finding.get("signal")
        context = finding.get("context")

        if context != "affirmed":
            continue

        if signal not in EVENT_TYPES:
            continue

        grouped[signal].append(finding)

    events = []

    for signal, findings in grouped.items():
        event_type, title = EVENT_TYPES[signal]

        event = ClinicalEvent(
            patient_id=patient_id,
            source="audio_analysis",
            event_type=event_type,
            severity=Severity.LOW.value,
            title=title,
            description=(
                "Expressão identificada por regras determinísticas "
                "em áudio sintético. Requer avaliação contextual "
                "e não representa diagnóstico."
            ),
            payload={
                "job_id": job_id,
                "media_file_id": media_file_id,
                "signal": signal,
                "context": "affirmed",
                "findings": findings,
                "requires_human_review": True,
                "analyzer": text_analysis.get("analyzer"),
                "disclaimer": (
                    "Evento demonstrativo. "
                    "Não utilizar para decisões clínicas."
                ),
            },
        )

        db.add(event)
        db.flush()
        events.append(event)

    return events
