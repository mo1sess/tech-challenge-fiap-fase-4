"""Azure AI Language opcional; nunca substitui as regras contextuais locais."""
import logging

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

from app.core.config import Settings

logger = logging.getLogger(__name__)


def analyze_language(text: str, settings: Settings) -> dict:
    result = {
        "provider": "azure_ai_language", "language": "pt",
        "status": "not_configured", "sentiment": None, "entities": [],
        "errors": [],
        "disclaimer": "Entidades gerais e sentimento linguístico; sem validação clínica.",
    }
    if not text.strip():
        result["status"] = "empty_text"
        return result
    if not settings.azure_language_endpoint or not settings.azure_language_key:
        return result
    try:
        with TextAnalyticsClient(
            endpoint=settings.azure_language_endpoint,
            credential=AzureKeyCredential(settings.azure_language_key),
            retry_total=1, connection_timeout=5, read_timeout=15,
        ) as client:
            for operation in ("sentiment", "entities"):
                try:
                    method = client.analyze_sentiment if operation == "sentiment" else client.recognize_entities
                    document = method([text], language="pt")[0]
                    if document.is_error:
                        # Não persistir mensagens do provedor: podem conter texto ou URLs sensíveis.
                        result["errors"].append({"operation": operation, "reason": "document_error"})
                        continue
                    if operation == "sentiment":
                        scores = document.confidence_scores
                        result["sentiment"] = {
                            "label": document.sentiment,
                            "confidence_scores": {name: float(getattr(scores, name)) for name in ("positive", "neutral", "negative")},
                        }
                    else:
                        result["entities"] = [{
                            "text": e.text, "category": e.category,
                            "subcategory": e.subcategory, "confidence_score": float(e.confidence_score),
                            "offset": e.offset, "length": e.length,
                        } for e in document.entities]
                except Exception:
                    logger.warning("Azure Language: falha na operação %s; análise local preservada", operation)
                    result["errors"].append({"operation": operation, "reason": "service_error"})
        result["status"] = "partial" if len(result["errors"]) == 1 else "error" if result["errors"] else "completed"
    except Exception:
        logger.warning("Azure Language indisponível; análise local preservada")
        result["status"] = "error"
        result["errors"].append({"operation": "client", "reason": "service_unavailable"})
    return result
