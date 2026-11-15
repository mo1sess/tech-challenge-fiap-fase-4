import asyncio

from azure.ai.textanalytics import HealthcareEntity
from azure.ai.textanalytics.aio import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError

from app.core.config import Settings
from app.modules.audio.azure_language import exceeds_language_request_limit

LANGUAGE = "pt"
MAX_TEXT_ELEMENTS = 125_000
OPERATION_TIMEOUT_SECONDS = 20
CLINICAL_MENTIONS_DISCLAIMER = (
    "Menções extraídas da transcrição sintética para revisão humana e uso educacional. "
    "O escore representa a confiança na extração do trecho."
)


def _serialize_mention(entity: HealthcareEntity) -> dict[str, object]:
    assertion = entity.assertion
    return {
        "text": entity.text,
        "category": entity.category,
        "offset": entity.offset,
        "length": entity.length,
        "confidence_score": entity.confidence_score,
        "context": {
            "certainty": assertion.certainty if assertion else None,
            "association": assertion.association if assertion else None,
            "conditionality": assertion.conditionality if assertion else None,
        },
    }


async def analyze_clinical_mentions(text: str | None, settings: Settings) -> dict[str, object]:
    result = {
        "provider": "azure_text_analytics_for_health",
        "language": LANGUAGE,
        "disclaimer": CLINICAL_MENTIONS_DISCLAIMER,
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
        async with TextAnalyticsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
            logging_enable=False,
            connection_timeout=5,
            read_timeout=10,
            retry_total=0,
        ) as client:
            async with asyncio.timeout(OPERATION_TIMEOUT_SECONDS):
                poller = await client.begin_analyze_healthcare_entities(
                    [text],
                    language=LANGUAGE,
                    disable_service_logs=True,
                    polling_interval=1,
                )
                documents = [document async for document in await poller.result()]

        if len(documents) != 1:
            return {**result, "status": "unavailable", "reason": "invalid_response"}
        document = documents[0]
        if document.is_error:
            return {**result, "status": "unavailable", "reason": "document_error"}

        mentions = [
            _serialize_mention(entity)
            for entity in document.entities
            if entity.category == "SymptomOrSign"
        ]
    except TimeoutError:
        return {**result, "status": "unavailable", "reason": "timeout"}
    except (AzureError, ValueError):
        return {**result, "status": "unavailable", "reason": "service_error"}
    except (AttributeError, KeyError, TypeError):
        return {**result, "status": "unavailable", "reason": "invalid_response"}

    return {**result, "status": "succeeded", "mentions": mentions}
