from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ClinicalMeasurement, Severity


@dataclass(frozen=True)
class TrendDetection:
    code: str
    metric: str
    severity: Severity
    values: list[float]
    reason: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        return payload


def _series(measurements: list[ClinicalMeasurement], attribute: str) -> list[float]:
    values = [getattr(item, attribute) for item in measurements]
    return [float(value) for value in values if value is not None]


def evaluate_recent_trends(
    db: Session,
    patient_id: str,
    *,
    window_size: int = 4,
) -> list[TrendDetection]:
    """Apply transparent trend rules to recent synthetic measurements."""
    statement = (
        select(ClinicalMeasurement)
        .where(
            ClinicalMeasurement.patient_id == patient_id,
            ClinicalMeasurement.is_synthetic.is_(True),
        )
        .order_by(ClinicalMeasurement.measured_at.desc())
        .limit(window_size)
    )
    measurements = list(reversed(list(db.scalars(statement))))
    if len(measurements) < window_size:
        return []

    detections: list[TrendDetection] = []
    heart_rate = _series(measurements, "heart_rate_bpm")
    if (
        len(heart_rate) == window_size
        and all(current >= previous for previous, current in zip(heart_rate, heart_rate[1:]))
        and heart_rate[-1] - heart_rate[0] >= 25
    ):
        detections.append(
            TrendDetection(
                code="rising_heart_rate",
                metric="heart_rate_bpm",
                severity=Severity.HIGH,
                values=heart_rate,
                reason="aumento monotônico demonstrativo na janela recente",
            )
        )

    spo2 = _series(measurements, "spo2_percent")
    if (
        len(spo2) == window_size
        and all(current <= previous for previous, current in zip(spo2, spo2[1:]))
        and spo2[0] - spo2[-1] >= 4
    ):
        detections.append(
            TrendDetection(
                code="falling_spo2",
                metric="spo2_percent",
                severity=Severity.HIGH,
                values=spo2,
                reason="queda monotônica demonstrativa na janela recente",
            )
        )

    systolic = _series(measurements, "systolic_mmhg")
    if len(systolic) == window_size and max(systolic) - min(systolic) >= 35:
        detections.append(
            TrendDetection(
                code="systolic_variability",
                metric="systolic_mmhg",
                severity=Severity.MEDIUM,
                values=systolic,
                reason="variação demonstrativa elevada na janela recente",
            )
        )

    return detections
