import asyncio
import json
from unittest.mock import MagicMock

import pytest
from azure.ai.textanalytics import (
    AnalyzeHealthcareEntitiesResult,
    DocumentError,
    HealthcareEntity,
    HealthcareEntityAssertion,
    TextAnalyticsError,
)
from azure.core.exceptions import ServiceRequestError

from app.core.config import Settings
from app.modules.audio.azure_healthcare import MAX_TEXT_ELEMENTS, analyze_clinical_mentions

pytestmark = pytest.mark.anyio


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        azure_language_endpoint="https://language.example.invalid",
        azure_language_key="dummy-key",
    )


@pytest.fixture
def sdk_client(monkeypatch):
    factory = MagicMock()
    monkeypatch.setattr("app.modules.audio.azure_healthcare.TextAnalyticsClient", factory)
    return factory


async def pages(*documents):
    for document in documents:
        yield document


async def test_serializes_mentions_and_preserves_context(sdk_client, settings):
    text = "Estou com dor. Minha irmã não tem febre."
    client = sdk_client.return_value.__aenter__.return_value
    poller = client.begin_analyze_healthcare_entities.return_value
    poller.result.return_value = pages(
        AnalyzeHealthcareEntitiesResult(
            entities=[
                HealthcareEntity(
                    text="dor", category="SymptomOrSign", offset=10, length=3, confidence_score=0.93
                ),
                HealthcareEntity(
                    text="febre", category="SymptomOrSign", offset=34, length=5, confidence_score=0.87,
                    assertion=HealthcareEntityAssertion(
                        certainty="negative", association="other", conditionality="hypothetical"
                    ),
                ),
                HealthcareEntity(text="ibuprofeno", category="MedicationName"),
            ]
        )
    )

    result = json.loads(json.dumps(await analyze_clinical_mentions(text, settings)))

    assert result["status"] == "succeeded"
    assert result["provider"] == "azure_text_analytics_for_health"
    assert result["language"] == "pt"
    assert result["mentions"] == [
        {
            "text": "dor", "category": "SymptomOrSign", "offset": 10, "length": 3,
            "confidence_score": 0.93,
            "context": {"certainty": None, "association": None, "conditionality": None},
        },
        {
            "text": "febre", "category": "SymptomOrSign", "offset": 34, "length": 5,
            "confidence_score": 0.87,
            "context": {"certainty": "negative", "association": "other", "conditionality": "hypothetical"},
        },
    ]
    assert sdk_client.call_args.kwargs["endpoint"] == settings.azure_language_endpoint
    client.begin_analyze_healthcare_entities.assert_awaited_once_with(
        [text], language="pt", disable_service_logs=True, polling_interval=1
    )


@pytest.mark.parametrize(
    ("text", "status", "reason"),
    [
        (None, "skipped", "speech_not_recognized"),
        (" ", "skipped", "empty_text"),
        ("a" * (MAX_TEXT_ELEMENTS + 1), "unavailable", "document_too_large"),
    ],
    ids=["no-match", "empty", "oversized"],
)
async def test_skips_sdk_when_text_cannot_be_submitted(sdk_client, settings, text, status, reason):
    result = await analyze_clinical_mentions(text, settings)
    assert result["status"] == status
    assert result["reason"] == reason
    sdk_client.assert_not_called()


async def test_missing_configuration(sdk_client, settings):
    settings.azure_language_key = None
    result = await analyze_clinical_mentions("Estou com dor.", settings)
    assert result["status"] == "unavailable"
    assert result["reason"] == "missing_configuration"
    sdk_client.assert_not_called()


async def test_no_symptoms_is_a_success(sdk_client, settings):
    client = sdk_client.return_value.__aenter__.return_value
    client.begin_analyze_healthcare_entities.return_value.result.return_value = pages(
        AnalyzeHealthcareEntitiesResult(entities=[])
    )
    result = await analyze_clinical_mentions("O passeio foi horrível.", settings)
    assert result["status"] == "succeeded"
    assert result["mentions"] == []


@pytest.mark.parametrize("reason", ["timeout", "service_error", "document_error", "invalid_response"])
async def test_azure_failures_are_safe(sdk_client, settings, monkeypatch, reason):
    client = sdk_client.return_value.__aenter__.return_value
    operation = client.begin_analyze_healthcare_entities
    poller = operation.return_value
    if reason == "timeout":
        monkeypatch.setattr("app.modules.audio.azure_healthcare.OPERATION_TIMEOUT_SECONDS", 0.01)
        async def delayed_result():
            await asyncio.sleep(60)

        poller.result.side_effect = delayed_result
    elif reason == "service_error":
        operation.side_effect = ServiceRequestError("private failure detail")
    elif reason == "document_error":
        poller.result.return_value = pages(DocumentError(error=TextAnalyticsError(message="private failure detail")))
    else:
        poller.result.return_value = pages()

    result = await analyze_clinical_mentions("Estou com dor.", settings)
    assert result["status"] == "unavailable"
    assert result["reason"] == reason
    assert "private failure detail" not in json.dumps(result)
    sdk_client.return_value.__aexit__.assert_awaited_once()
