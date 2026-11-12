
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

HISTORICAL_MARKERS = {
    "ontem",
    "anteriormente",
    "semana passada",
    "mes passado",
}

THIRD_PARTY_MARKERS = {
    "minha mae",
    "meu pai",
    "meu filho",
    "minha filha",
    "meu amigo",
    "minha amiga",
    "ele",
    "ela",
}


@dataclass(frozen=True)
class TextFinding:
    signal: str
    expression: str
    context: str
    evidence: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TextAnalysis:
    analyzer: str
    matched_signals: list[str]
    matched_expressions: list[str]
    requires_review: bool
    findings: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )
    normalized = normalized.lower()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def classify_context(
    sentence: str,
    expression: str,
    match_start: int,
) -> str:
    # Context is evaluated within a sentence, not globally.
    prefix = sentence[:match_start]
    preceding_tokens = prefix.split()
    recent_tokens = preceding_tokens[-5:]

    # "Nao consigo respirar" is itself an affirmative
    # report of difficulty, despite containing "nao".
    if expression == "nao consigo respirar":
        return "affirmed"

    # Conservative negation detection close to the expression.
    if "nao" in recent_tokens or "sem" in recent_tokens:
        return "negated"

    if any(
        marker in sentence
        for marker in THIRD_PARTY_MARKERS
    ):
        return "third_party"

    if any(
        marker in sentence
        for marker in HISTORICAL_MARKERS
    ) or re.search(r"\bestava com dor\b", sentence):
        return "historical"

    return "affirmed"


def analyze_text(text: str) -> TextAnalysis:
    findings = []
    matched_signals = []
    matched_expressions = []
    seen = set()

    sentences = re.split(r"[.!?;\n]+", text)

    for raw_sentence in sentences:
        sentence = normalize_text(raw_sentence)

        if not sentence:
            continue

        for signal, expressions in PATTERNS.items():
            for expression in expressions:
                normalized_expression = normalize_text(expression)

                regex = (
                    r"(?<!\w)"
                    + re.escape(normalized_expression)
                    + r"(?!\w)"
                )

                for match in re.finditer(regex, sentence):
                    context = classify_context(
                        sentence,
                        normalized_expression,
                        match.start(),
                    )

                    key = (
                        signal,
                        normalized_expression,
                        context,
                        sentence,
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    finding = TextFinding(
                        signal=signal,
                        expression=expression,
                        context=context,
                        evidence=sentence,
                    )
                    findings.append(finding.to_dict())

                    # Only affirmative matches enter the legacy
                    # matched_signals and matched_expressions fields.
                    if context == "affirmed":
                        if signal not in matched_signals:
                            matched_signals.append(signal)

                        if expression not in matched_expressions:
                            matched_expressions.append(expression)

    return TextAnalysis(
        analyzer="deterministic_context_rules_v2",
        matched_signals=matched_signals,
        matched_expressions=matched_expressions,
        requires_review=any(
            item["context"] in {"affirmed", "third_party"}
            for item in findings
        ),
        findings=findings,
    )
