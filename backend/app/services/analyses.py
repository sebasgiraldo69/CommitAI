from datetime import datetime
from uuid import uuid4

from pydantic import ValidationError

from backend.app.ai.provider import ExtractionProvider, invalid_response
from backend.app.domain.commitments import (
    public_record,
    timestamp,
    utc_now,
)
from backend.app.schemas.analyses import (
    AnalysisRequest,
    ExtractionOutput,
)


def analyze_text(
    request: AnalysisRequest,
    provider: ExtractionProvider,
    now: datetime | None = None,
) -> dict:
    now = now or utc_now()

    raw = provider.generate(request.model_dump(mode="json"))

    try:
        output = ExtractionOutput.model_validate(raw)
    except ValidationError:
        raise invalid_response() from None

    candidates = []

    for candidate in output.candidates:
        values = candidate.values.model_dump(mode="json")
        extraction = candidate.extraction.model_dump(mode="json")

        if extraction["source_quote"] not in request.text:
            raise invalid_response()

        for ambiguity in extraction["ambiguities"]:
            if ambiguity["source_text"] not in request.text:
                raise invalid_response()

            # Si el modelo reconoce ambigüedad, no conservar un
            # valor que parezca preciso para ese mismo campo.
            values[ambiguity["field"]] = None

        # La zona proviene de la solicitud, no de una inferencia.
        values["timezone"] = request.timezone

        if extraction["priority_origin"] == "default":
            values["priority"] = "medium"

        record = {
            **values,
            "extraction": extraction,
            "resolved_ambiguities": [],
            "lifecycle": "open",
        }

        computed = public_record(record, now)

        candidates.append(
            {
                "candidate_id": str(uuid4()),
                "values": values,
                **extraction,
                "missing_information": computed["missing_information"],
                "status": computed["status"],
            }
        )

    return {
        "analysis_id": str(uuid4()),
        "reference_date": request.reference_date.isoformat(),
        "timezone": request.timezone,
        "source": request.source.model_dump(mode="json"),
        "candidates": candidates,
        "analyzed_at": timestamp(now),
    }