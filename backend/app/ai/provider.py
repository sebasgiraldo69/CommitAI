import json
from typing import Protocol

import httpx

from backend.app.ai.prompts import SYSTEM_PROMPT
from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import AppError
from backend.app.schemas.analyses import ExtractionOutput


class ExtractionProvider(Protocol):
    def generate(self, payload: dict) -> dict:
        ...


def strict_schema() -> dict:
    schema = ExtractionOutput.model_json_schema()

    def visit(value):
        if isinstance(value, dict):
            value.pop("default", None)

            if value.get("type") == "object":
                value["additionalProperties"] = False
                value["required"] = list(value.get("properties", {}))

            for child in value.values():
                visit(child)

        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    return schema


def invalid_response() -> AppError:
    return AppError(
        "provider_invalid_response",
        "La IA devolvió una respuesta inválida o incompleta.",
        502,
    )


class OpenAIProvider:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ):
        self.settings = settings
        self.transport = transport

    def generate(self, payload: dict) -> dict:
        settings = self.settings

        if (
            settings.ai_provider != "openai"
            or not settings.ai_configured
        ):
            raise AppError(
                "ai_not_configured",
                "Configura AI_PROVIDER, AI_MODEL y AI_API_KEY.",
                503,
            )

        body = {
            "model": settings.ai_model,
            "instructions": SYSTEM_PROMPT,
            "input": json.dumps(payload, ensure_ascii=False),
            "store": False,
            "max_output_tokens": 8192,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "commitment_extraction",
                    "strict": True,
                    "schema": strict_schema(),
                }
            },
        }

        timeout = httpx.Timeout(
            settings.ai_read_timeout_seconds,
            connect=settings.ai_connect_timeout_seconds,
        )

        try:
            with httpx.Client(
                timeout=timeout,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                response = client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {settings.ai_api_key}"
                    },
                    json=body,
                )
        except httpx.TimeoutException:
            raise AppError(
                "provider_timeout",
                "La IA no respondió a tiempo. Puedes reintentar.",
                504,
            ) from None
        except httpx.RequestError:
            raise AppError(
                "provider_unavailable",
                "No se pudo conectar con el proveedor de IA.",
                503,
            ) from None

        if response.status_code in (401, 403):
            raise AppError(
                "provider_auth",
                "Revisa la clave y los permisos del proyecto de API.",
                503,
            )

        if response.status_code == 429:
            raise AppError(
                "provider_quota",
                "El proveedor indicó un límite de cuota o solicitudes.",
                503,
            )

        if response.status_code in (400, 404):
            raise AppError(
                "provider_request",
                "El proveedor rechazó el modelo o el formato solicitado.",
                502,
            )

        if response.status_code != 200:
            raise AppError(
                "provider_unavailable",
                "El proveedor no pudo completar la solicitud.",
                503,
            )

        try:
            data = response.json()

            if not isinstance(data, dict):
                raise ValueError()

            if data.get("status") != "completed":
                raise ValueError()

            parts = [
                part
                for item in data["output"]
                if item.get("type") == "message"
                for part in item.get("content", [])
            ]

            if any(part.get("type") == "refusal" for part in parts):
                raise AppError(
                    "provider_refusal",
                    "La IA no pudo analizar este texto.",
                    502,
                )

            output = "".join(
                part["text"]
                for part in parts
                if part.get("type") == "output_text"
            )

            parsed = json.loads(output)

            if not isinstance(parsed, dict):
                raise ValueError()

            return parsed

        except (ValueError, KeyError, TypeError, AttributeError):
            raise invalid_response() from None


def get_provider() -> ExtractionProvider:
    return OpenAIProvider(get_settings())