import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.domain.commitments import public_record
from backend.app.main import app

NOW = datetime(2026, 10, 15, 17, 0, tzinfo=timezone.utc)


def example_payload():
    return {
        "analysis_id": str(uuid4()),
        "reference_date": "2026-10-15",
        "source": {"kind": "text"},
        "items": [
            {
                "candidate_id": str(uuid4()),
                "values": {
                    "title": "Revisar contrato",
                    "responsible": "Ana",
                    "due_date": "2026-10-16",
                },
                "extraction": {
                    "source_quote": "Ana revisará el contrato mañana.",
                    "confidence": 0.9,
                    "priority_origin": "default",
                },
            }
        ],
    }


class CommitmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        settings = replace(
            get_settings(),
            database_path=Path(self.temp.name) / "test.db",
        )
        self.settings_patch = patch(
            "backend.app.db.database.get_settings",
            return_value=settings,
        )
        self.settings_patch.start()

        self.clock_patch = patch(
            "backend.app.services.commitments.utc_now",
            return_value=NOW,
        )
        self.clock_patch.start()

        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.clock_patch.stop()
        self.settings_patch.stop()
        self.temp.cleanup()

    def create_one(self):
        response = self.client.post(
            "/api/commitments",
            headers={"Idempotency-Key": str(uuid4())},
            json=example_payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["items"][0]

    def test_idempotency_and_conflict(self):
        payload = example_payload()
        headers = {"Idempotency-Key": str(uuid4())}

        first = self.client.post(
            "/api/commitments", headers=headers, json=payload
        )
        repeated = self.client.post(
            "/api/commitments", headers=headers, json=payload
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(first.json(), repeated.json())

        payload["items"][0]["values"]["title"] = "Otra tarea"
        conflict = self.client.post(
            "/api/commitments", headers=headers, json=payload
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(
            self.client.get("/api/commitments").json()["total"], 1
        )

    def test_close_and_reopen(self):
        item = self.create_one()
        url = f"/api/commitments/{item['id']}"

        completed = self.client.patch(url, json={"action": "complete"})
        self.assertEqual(completed.json()["status"], "completed")

        changed = self.client.patch(
            url,
            json={"changes": {"due_date": "2026-10-14"}},
        )
        self.assertEqual(changed.json()["status"], "completed")

        reopened = self.client.patch(url, json={"action": "reopen"})
        self.assertEqual(reopened.json()["status"], "overdue")

    def test_invalid_transition_rolls_back_changes(self):
        item = self.create_one()
        url = f"/api/commitments/{item['id']}"

        response = self.client.patch(
            url,
            json={
                "changes": {"responsible": None},
                "action": "set_pending",
            },
        )

        self.assertEqual(response.status_code, 409)
        persisted = self.client.get(url).json()
        self.assertEqual(persisted["responsible"], "Ana")

    def test_invalid_batch_does_not_create_records(self):
        payload = example_payload()
        invalid = example_payload()["items"][0]
        invalid["values"]["title"] = ""
        payload["items"].append(invalid)

        response = self.client.post(
            "/api/commitments",
            headers={"Idempotency-Key": str(uuid4())},
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.client.get("/api/commitments").json()["total"], 0
        )

    def test_persistence_after_application_restart(self):
        item = self.create_one()
        self.client.__exit__(None, None, None)
        self.client = TestClient(app)
        self.client.__enter__()

        response = self.client.get(f"/api/commitments/{item['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Revisar contrato")

    def test_filters_and_counts(self):
        item = self.create_one()
        self.client.patch(
            f"/api/commitments/{item['id']}",
            json={"action": "complete"},
        )

        response = self.client.get(
            "/api/commitments",
            params={"status": "pending", "responsible": "ana"},
        )
        body = response.json()

        self.assertEqual(body["total"], 0)
        self.assertEqual(body["counts"]["completed"], 1)

    def test_end_of_day_and_incomplete_precedence(self):
        item = self.create_one()
        record = {**item, "lifecycle": "open", "due_date": "2026-10-15"}

        before = datetime(2026, 10, 16, 4, 59, 59, tzinfo=timezone.utc)
        boundary = datetime(2026, 10, 16, 5, 0, tzinfo=timezone.utc)

        self.assertEqual(public_record(record, before)["status"], "pending")
        self.assertEqual(public_record(record, boundary)["status"], "overdue")

        record["responsible"] = None
        result = public_record(record, boundary)

        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(result["is_past_due"])


if __name__ == "__main__":
    unittest.main()