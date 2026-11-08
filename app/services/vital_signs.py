from dataclasses import dataclass

from app.db.models import ClinicalMeasurement, Severity


DISCLAIMER = (
    "Dados e limites exclusivamente sinteticos e educacionais. "
    "O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."
)


@dataclass(frozen=True)
class Detection:
    metric: str
    value: float
    severity: Severity
    reason: str


SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def evaluate_vital_signs(measurement: ClinicalMeasurement) -> list[Detection]:
    """Apply illustrative rules to synthetic values only."""
    detections: list[Detection] = []

    if measurement.heart_rate_bpm is not None:
        value = measurement.heart_rate_bpm
        if value < 40 or value > 140:
            detections.append(Detection("heart_rate_bpm", value, Severity.CRITICAL, "fora da faixa critica demonstrativa"))
        elif value < 50 or value > 120:
            detections.append(Detection("heart_rate_bpm", value, Severity.HIGH, "fora da faixa de atencao demonstrativa"))

    if measurement.spo2_percent is not None:
        value = measurement.spo2_percent
        if value < 88:
            detections.append(Detection("spo2_percent", value, Severity.CRITICAL, "abaixo do limite critico demonstrativo"))
        elif value < 92:
            detections.append(Detection("spo2_percent", value, Severity.HIGH, "abaixo do limite de atencao demonstrativo"))

    if measurement.systolic_mmhg is not None:
        value = measurement.systolic_mmhg
        if value < 80 or value > 200:
            detections.append(Detection("systolic_mmhg", value, Severity.CRITICAL, "fora da faixa critica demonstrativa"))
        elif value < 90 or value > 180:
            detections.append(Detection("systolic_mmhg", value, Severity.HIGH, "fora da faixa de atencao demonstrativa"))

    if measurement.diastolic_mmhg is not None:
        value = measurement.diastolic_mmhg
        if value < 50 or value > 130:
            detections.append(Detection("diastolic_mmhg", value, Severity.HIGH, "fora da faixa de atencao demonstrativa"))
        elif value < 60 or value > 120:
            detections.append(Detection("diastolic_mmhg", value, Severity.MEDIUM, "requer revisao demonstrativa"))

    return detections


def highest_severity(detections: list[Detection]) -> Severity:
    return max((item.severity for item in detections), key=SEVERITY_RANK.__getitem__)

