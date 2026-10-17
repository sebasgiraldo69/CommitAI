import unittest
from dataclasses import replace
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.ai.provider import OpenAIProvider, get_provider
from backend.app.api.routes.analyses import router
from backend.app.core.config import get_settings
from backend.app.core.errors import AppError, register_error_handlers
from backend.app.schemas.analyses import AnalysisRequest
from backend.app.services.analyses import analyze_text

NOW = datetime(2026, 10, 15, 17, 0, tzinfo=timezone.utc)


def example_output():
    return {
        "candidates": [
            {
                "values": {
                    "title": "Enviar propuesta",
                    "responsible": "Ana",
                    "due_date": "2026-10-16",
                },
                "extraction": {
                    "source_quote": "Enviaré la propuesta mañana.",
                    "confidence": 0.9,
                    "priority_origin": "default",
                    "ambiguities": [],
                },
            }
        ]
    }


class FakeProvider:
    def __init__(self, output):
        self.output = output

    def generate(self, payload):
        return self.output


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.request = AnalysisRequest(
            text="Enviaré la propuesta mañana.",
            reference_date="2026-10-15",
            speaker="Ana",
        )

    def test_candidate_is_validated(self):
        result = analyze_text(
            self.request,
            FakeProvider(example_output()),
            NOW,
        )

        candidate = result["candidates"][0]

        self.assertEqual(candidate["status"], "pending")
        self.assertEqual(candidate["missing_information"], [])
        self.assertEqual(candidate["values"]["due_time"], None)

    def test_missing_responsible_is_incomplete(self):
        output = example_output()
        output["candidates"][0]["values"]["responsible"] = None

        result = analyze_text(self.request, FakeProvider(output), NOW)
        candidate = result["candidates"][0]

        self.assertEqual(candidate["status"], "incomplete")
        self.assertEqual(
            candidate["missing_information"],
            ["responsible"],
        )

    def test_no_commitments(self):
        result = analyze_text(
            self.request,
            FakeProvider({"candidates": []}),
            NOW,
        )
        self.assertEqual(result["candidates"], [])

    def test_invented_quote_is_rejected(self):
        output = example_output()
        output["candidates"][0]["extraction"]["source_quote"] = (
            "Una frase que no aparece."
        )

        with self.assertRaises(AppError) as captured:
            analyze_text(self.request, FakeProvider(output), NOW)

        self.assertEqual(
            captured.exception.code,
            "provider_invalid_response",
        )

    def test_invalid_output_is_rejected(self):
        with self.assertRaises(AppError):
            analyze_text(
                self.request,
                FakeProvider({"candidates": "incorrecto"}),
                NOW,
            )

    def test_ambiguous_time_is_not_invented(self):
        request = AnalysisRequest(
            text="Ana enviará la propuesta mañana a las 4.",
            reference_date="2026-10-15",
        )
        output = example_output()
        candidate = output["candidates"][0]
        candidate["values"]["due_time"] = "16:00"
        candidate["extraction"]["source_quote"] = request.text
        candidate["extraction"]["ambiguities"] = [
            {
                "field": "due_time",
                "reason": "Falta indicar mañana o tarde.",
                "source_text": "a las 4",
            }
        ]

        result = analyze_text(request, FakeProvider(output), NOW)
        candidate = result["candidates"][0]

        self.assertIsNone(candidate["values"]["due_time"])
        self.assertIn("due_time", candidate["missing_information"])

    def test_route_without_database(self):
        # Esta aplicación de prueba no tiene base de datos.
        app = FastAPI()
        register_error_handlers(app)
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_provider] = lambda: FakeProvider(
            {"candidates": []}
        )

        from backend.app.api.deps import get_current_user

        app.dependency_overrides[get_current_user] = lambda: {
            "id": "test-user-id",
            "email": "test@commitai.local",
            "created_at": "2026-10-15T17:00:00Z",
        }

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/analyses",
                    json=self.request.model_dump(mode="json"),
                )
                invalid = client.post(
                    "/api/analyses",
                    json={"text": "   ", "reference_date": "2026-10-15"},
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candidates"], [])
        self.assertEqual(invalid.status_code, 422)

    def test_missing_key(self):
        settings = replace(
            get_settings(),
            ai_provider="openai",
            ai_model="gpt-4.1-mini",
            ai_api_key="",
        )

        with self.assertRaises(AppError) as captured:
            OpenAIProvider(settings).generate({})

        self.assertEqual(captured.exception.code, "ai_not_configured")

    def test_provider_http_errors(self):
        settings = replace(
            get_settings(),
            ai_provider="openai",
            ai_model="gpt-4.1-mini",
            ai_api_key="fake-test-key",
        )

        for status, code in [
            (401, "provider_auth"),
            (429, "provider_quota"),
            (500, "provider_unavailable"),
        ]:
            with self.subTest(status=status):
                transport = httpx.MockTransport(
                    lambda request, status=status: httpx.Response(
                        status,
                        json={},
                    )
                )
                provider = OpenAIProvider(settings, transport)

                with self.assertRaises(AppError) as captured:
                    provider.generate({})

                self.assertEqual(captured.exception.code, code)

    def test_provider_timeout(self):
        settings = replace(
            get_settings(),
            ai_provider="openai",
            ai_model="gpt-4.1-mini",
            ai_api_key="fake-test-key",
        )

        def timeout(request):
            raise httpx.ReadTimeout("test", request=request)

        provider = OpenAIProvider(
            settings,
            httpx.MockTransport(timeout),
        )

        with self.assertRaises(AppError) as captured:
            provider.generate({})

        self.assertEqual(captured.exception.code, "provider_timeout")


if __name__ == "__main__":
    unittest.main()