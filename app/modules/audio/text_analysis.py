
import re
import unicodedata
from dataclasses import asdict, dataclass

PATTERNS = {
    "help_request": [
        "preciso de ajuda",
        "me ajude",
        "socorro",
    ],
    "pain_report": [
        "estou com dor",
        "sinto dor",
        "dor de cabeca",
    ],
    "breathing_report": [
        "falta de ar",
        "dificuldade para respirar",
        "nao consigo respirar",
    ],
}


@dataclass(frozen=True)
class TextAnalysis:
    analyzer: str
    matched_signals: list[str]
    matched_expressions: list[str]
    requires_review: bool

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )
    text = text.lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def analyze_text(text: str) -> TextAnalysis:
    normalized = normalize_text(text)

    signals = []
    expressions_found = []

    for signal, expressions in PATTERNS.items():
        for expression in expressions:
            normalized_expression = normalize_text(expression)

            regex = (
                r"(?<!\w)"
                + re.escape(normalized_expression)
                + r"(?!\w)"
            )

            if re.search(regex, normalized):
                if signal not in signals:
                    signals.append(signal)
                expressions_found.append(expression)

    return TextAnalysis(
        analyzer="deterministic_rules_v1",
        matched_signals=signals,
        matched_expressions=expressions_found,
        requires_review=bool(signals),
    )
