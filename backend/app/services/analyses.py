import logging
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

logger = logging.getLogger("commitai.analyses")


def analyze_text(
    request: AnalysisRequest,
    provider: ExtractionProvider,
    now: datetime | None = None,
) -> dict:
    now = now or utc_now()

    raw = provider.generate(request.model_dump(mode="json"))

    try:
        output = ExtractionOutput.model_validate(raw)
    except ValidationError as exc:
        logger.error(
            "Error de validación en ExtractionOutput: %s. raw=%s",
            exc,
            raw,
        )
        raise invalid_response() from None

    candidates = []

    for candidate in output.candidates:
        values = candidate.values.model_dump(mode="json")
        extraction = candidate.extraction.model_dump(mode="json")

        quote = (
            extraction["source_quote"]
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .strip()
        )
        text = request.text.replace("\r\n", "\n").replace("\r", "\n")

        if quote not in text:
            if quote.rstrip(".") in text:
                extraction["source_quote"] = quote.rstrip(".")
            elif (quote + ".") in text:
                extraction["source_quote"] = quote + "."
            else:
                logger.warning(
                    "source_quote no encontrado en el texto original.\nsource_quote: %r\nrequest.text: %r",
                    quote,
                    text,
                )
                raise invalid_response()

        for ambiguity in extraction["ambiguities"]:
            ambiguity_text = (
                ambiguity["source_text"]
                .replace("\r\n", "\n")
                .replace("\r", "\n")
                .strip()
            )
            if ambiguity_text not in text:
                if ambiguity_text.rstrip(".") in text:
                    ambiguity["source_text"] = ambiguity_text.rstrip(".")
                elif (ambiguity_text + ".") in text:
                    ambiguity["source_text"] = ambiguity_text + "."
                else:
                    logger.warning(
                        "ambiguity source_text no encontrado en el texto original.\nsource_text: %r\nrequest.text: %r",
                        ambiguity_text,
                        text,
                    )
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