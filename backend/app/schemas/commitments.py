from datetime import date, time
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]

Status = Literal[
    "pending", "incomplete", "overdue", "completed", "discarded"
]

AmbiguousField = Literal["responsible", "due_date", "due_time"]

Action = Literal[
    "complete",
    "discard",
    "reopen",
    "set_pending",
    "set_incomplete",
    "set_overdue",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(StrictModel):
    kind: Literal["text", "email", "meeting", "other"] = "text"
    label: str | None = Field(default=None, max_length=500)
    external_id: str | None = Field(default=None, max_length=500)


class Ambiguity(StrictModel):
    field: AmbiguousField
    reason: str = Field(min_length=1, max_length=1000)
    source_text: str = Field(min_length=1, max_length=20000)


class Extraction(StrictModel):
    source_quote: str = Field(min_length=1, max_length=20000)
    confidence: float = Field(ge=0, le=1)
    priority_origin: Literal["explicit", "default"]
    ambiguities: list[Ambiguity] = Field(default_factory=list)


class Values(StrictModel):
    title: Name
    description: str | None = Field(default=None, max_length=2000)
    responsible: Name | None = None
    counterparty: Name | None = None
    due_date: date | None = None
    due_time: str | None = None
    timezone: str = "America/Bogota"
    priority: Literal["low", "medium", "high"] = "medium"
    condition: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "description",
        "responsible",
        "counterparty",
        "condition",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("due_date", mode="before")
    @classmethod
    def validate_date_format(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError("Usa YYYY-MM-DD.")
            return parsed
        if type(value) is date:
            return value
        raise ValueError("Usa una fecha ISO.")

    @field_validator("due_time")
    @classmethod
    def validate_time(cls, value):
        if value is None:
            return None
        parsed = time.fromisoformat(value)
        if len(value) != 5 or parsed.strftime("%H:%M") != value:
            raise ValueError("Usa HH:MM.")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Zona horaria inválida.") from None
        return value


class AcceptedItem(StrictModel):
    candidate_id: UUID
    values: Values
    extraction: Extraction
    resolved_ambiguities: list[AmbiguousField] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_resolutions(self):
        available = {
            ambiguity.field for ambiguity in self.extraction.ambiguities
        }
        resolved = self.resolved_ambiguities

        if len(resolved) != len(set(resolved)):
            raise ValueError("Hay ambigüedades resueltas repetidas.")

        if not set(resolved).issubset(available):
            raise ValueError("La ambigüedad resuelta no existe.")

        return self


class CreateBatch(StrictModel):
    analysis_id: UUID
    reference_date: date
    source: Source = Field(default_factory=Source)
    items: list[AcceptedItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_candidates(self):
        ids = [item.candidate_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Hay candidatos repetidos.")
        return self


class PatchCommitment(StrictModel):
    # Los valores se validan al combinarlos con el registro existente.
    changes: dict = Field(default_factory=dict)
    action: Action | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        allowed = set(Values.model_fields) | {"resolved_ambiguities"}

        if set(self.changes) - allowed:
            raise ValueError("Hay campos que no se pueden modificar.")

        if not self.changes and self.action is None:
            raise ValueError("Indica cambios o una acción.")

        return self