import json
from itertools import islice

import regex
from azure.ai.textanalytics import SentimentConfidenceScores, TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError

from app.core.config import Settings

LANGUAGE = "pt-BR"
MAX_TEXT_ELEMENTS = 5120
# Keep space for the SDK's request envelope within Azure's 1 MB limit.
MAX_ENCODED_TEXT_BYTES = 999_000
TEXT_ELEMENTS = regex.compile(r"\X")

SENTIMENT_DISCLAIMER = (
    "A classificação descreve o tom do texto e tem finalidade educacional. "
    "Os escores expressam a confiança do modelo na classificação. "
    "Sentimento negativo não indica risco clínico, dor, depressão ou emergência, "
    "e os escores não estimam a probabilidade de doença."
)


def _scores(scores: SentimentConfidenceScores) -> dict[str, float]:
    return {
        "positive": scores.positive,
        "neutral": scores.neutral,
        "negative": scores.negative,
    }


def exceeds_language_request_limit(text: str, max_text_elements: int) -> bool:
    elements = islice(TEXT_ELEMENTS.finditer(text), max_text_elements, None)
    return next(elements, None) is not None or len(json.dumps(text)) > MAX_ENCODED_TEXT_BYTES


def analyze_sentiment(text: str | None, settings: Settings) -> dict[str, object]:
    """Analyze one complete transcription. None represents unrecognized speech."""
    result = {
        "provider": "azure_ai_language",
        "language": LANGUAGE,
        "disclaimer": SENTIMENT_DISCLAIMER,
    }
    if text is None:
        return {**result, "status": "skipped", "reason": "speech_not_recognized"}
    if not text.strip():
        return {**result, "status": "skipped", "reason": "empty_text"}

    endpoint = (settings.azure_language_endpoint or "").strip()
    key = (settings.azure_language_key or "").strip()
    if not endpoint or not key:
        return {**result, "status": "unavailable", "reason": "missing_configuration"}

    if exceeds_language_request_limit(text, MAX_TEXT_ELEMENTS):
        return {**result, "status": "unavailable", "reason": "document_too_large"}

    try:
        with TextAnalyticsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
            logging_enable=False,
            connection_timeout=5,
            read_timeout=10,
            retry_total=0,
        ) as client:
            documents = client.analyze_sentiment(
                [text], language=LANGUAGE, disable_service_logs=True
            )
    except (AzureError, ValueError):
        return {**result, "status": "unavailable", "reason": "service_error"}
    except (AttributeError, KeyError, TypeError):
        return {**result, "status": "unavailable", "reason": "invalid_response"}

    if not documents or len(documents) != 1:
        return {**result, "status": "unavailable", "reason": "invalid_response"}

    document = documents[0]
    if document.is_error:
        return {**result, "status": "unavailable", "reason": "document_error"}

    return {
        **result,
        "status": "succeeded",
        "sentiment": document.sentiment,
        "confidence_scores": _scores(document.confidence_scores),
        "sentences": [
            {
                "text": sentence.text,
                "sentiment": sentence.sentiment,
                "confidence_scores": _scores(sentence.confidence_scores),
            }
            for sentence in document.sentences or []
        ],
    }
