from datetime import date

from pydantic import Field, field_validator

from backend.app.core.config import get_settings
from backend.app.schemas.commitments import (
    Extraction,
    Name,
    Source,
    StrictModel,
    Values,
)


class AnalysisRequest(StrictModel):
    text: str = Field(min_length=1, max_length=20000)
    reference_date: date
    timezone: str = Field(
        default_factory=lambda: get_settings().timezone
    )
    participants: list[Name] = Field(
        default_factory=list,
        max_length=50,
    )
    speaker: Name | None = None
    addressee: Name | None = None
    source: Source = Field(default_factory=Source)

    @field_validator("text", mode="before")
    @classmethod
    def normalize_text(cls, value):
        if isinstance(value, str):
            return value.replace("\r\n", "\n").replace("\r", "\n").strip()
        return value

    @field_validator("reference_date", mode="before")
    @classmethod
    def validate_reference_date(cls, value):
        return Values.validate_date_format(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value):
        return Values.validate_timezone(value)

    @field_validator("participants")
    @classmethod
    def unique_participants(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Hay participantes repetidos.")
        return value


class ExtractedCandidate(StrictModel):
    values: Values
    extraction: Extraction


class ExtractionOutput(StrictModel):
    candidates: list[ExtractedCandidate] = Field(max_length=100)