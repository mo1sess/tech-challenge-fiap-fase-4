from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ORMModel


class PatientCreate(ORMModel):
    code: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    alias: str = Field(min_length=2, max_length=120)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = Field(default=None, max_length=1000)
    is_synthetic: Literal[True] = True


class PatientRead(PatientCreate):
    id: str
    created_at: datetime

