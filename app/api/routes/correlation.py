
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.clinical import EventRead
from app.services.correlation_flow import correlate_audio_and_vitals
from app.services.correlation_v2 import correlate_multimodal_v2

router = APIRouter(tags=["multimodal correlation"])


@router.post(
    "/patients/{patient_id}/correlations/run-v2",
    response_model=list[EventRead],
    status_code=200,
)
def run_multimodal_correlation_v2(
    patient_id: str,
    window_minutes: int = Query(
        default=5,
        ge=1,
        le=60,
    ),
    db: Session = Depends(get_db),
) -> list:
    try:
        return correlate_multimodal_v2(
            db,
            patient_id=patient_id,
            window_minutes=window_minutes,
        )
    except ValueError as exc:
        status_code = (
            404 if str(exc) == "Patient not found" else 422
        )
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc



@router.post(
    "/patients/{patient_id}/correlations/run",
    response_model=list[EventRead],
    status_code=200,
)
def run_patient_correlation(
    patient_id: str,
    window_minutes: int = Query(
        default=5,
        ge=1,
        le=60,
    ),
    db: Session = Depends(get_db),
) -> list:
    try:
        return correlate_audio_and_vitals(
            db,
            patient_id=patient_id,
            window_minutes=window_minutes,
        )

    except ValueError as exc:
        if str(exc) == "Patient not found":
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
