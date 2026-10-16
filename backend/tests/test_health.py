import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class BaseApiTests(unittest.TestCase):
    def test_health(self):
        with TestClient(app) as client:
            response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertTrue(response.headers.get("X-Request-ID"))

    def test_not_found_has_standard_error(self):
        with TestClient(app) as client:
            response = client.get("/api/nonexistent")

        body = response.json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["error"]["code"], "not_found")
        self.assertEqual(
            body["request_id"],
            response.headers["X-Request-ID"],
        )


if __name__ == "__main__":
    unittest.main()