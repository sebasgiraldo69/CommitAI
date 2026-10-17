import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import app


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        settings = replace(
            get_settings(),
            database_path=Path(self.temp.name) / "test_auth.db",
        )
        self.settings_patch = patch(
            "backend.app.db.database.get_settings",
            return_value=settings,
        )
        self.settings_patch.start()

        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.settings_patch.stop()
        self.temp.cleanup()

    def test_register_success(self):
        res = self.client.post(
            "/api/auth/register",
            json={"email": "usuario@commitai.local", "password": "password123"},
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["email"], "usuario@commitai.local")
        self.assertTrue(bool(data["user"]["id"]))

    def test_register_duplicate_email(self):
        payload = {"email": "duplicado@commitai.local", "password": "password123"}
        first = self.client.post("/api/auth/register", json=payload)
        self.assertEqual(first.status_code, 201)

        second = self.client.post("/api/auth/register", json=payload)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["error"]["code"], "email_already_registered")

    def test_register_validation(self):
        # Correo inválido
        res = self.client.post(
            "/api/auth/register",
            json={"email": "no-es-correo", "password": "password123"},
        )
        self.assertEqual(res.status_code, 422)

        # Contraseña demasiado corta (< 6 caracteres)
        res2 = self.client.post(
            "/api/auth/register",
            json={"email": "corto@commitai.local", "password": "123"},
        )
        self.assertEqual(res2.status_code, 422)

    def test_login_and_me(self):
        # Registro
        self.client.post(
            "/api/auth/register",
            json={"email": "login@commitai.local", "password": "secreto123"},
        )

        # Login correcto
        login_res = self.client.post(
            "/api/auth/login",
            json={"email": "login@commitai.local", "password": "secreto123"},
        )
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]

        # Acceder a /api/auth/me con el token
        me_res = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["email"], "login@commitai.local")

        # Login con contraseña errónea
        bad_pass = self.client.post(
            "/api/auth/login",
            json={"email": "login@commitai.local", "password": "wrongpassword"},
        )
        self.assertEqual(bad_pass.status_code, 401)
        self.assertEqual(bad_pass.json()["error"]["code"], "invalid_credentials")

        # Login con usuario inexistente
        no_user = self.client.post(
            "/api/auth/login",
            json={"email": "fantasma@commitai.local", "password": "password123"},
        )
        self.assertEqual(no_user.status_code, 401)

    def test_unauthorized_and_invalid_token(self):
        # Sin token
        unauth = self.client.get("/api/auth/me")
        self.assertEqual(unauth.status_code, 401)

        # Token corrupto / inválido
        bad_token = self.client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer este-token-es-falso"},
        )
        self.assertEqual(bad_token.status_code, 401)

    def test_user_isolation(self):
        # Crear usuario A y usuario B
        res_a = self.client.post(
            "/api/auth/register",
            json={"email": "userA@commitai.local", "password": "password123"},
        )
        token_a = res_a.json()["access_token"]

        res_b = self.client.post(
            "/api/auth/register",
            json={"email": "userB@commitai.local", "password": "password123"},
        )
        token_b = res_b.json()["access_token"]

        # Usuario A crea un compromiso
        payload = {
            "analysis_id": str(uuid4()),
            "reference_date": "2026-10-15",
            "source": {"kind": "text"},
            "items": [
                {
                    "candidate_id": str(uuid4()),
                    "values": {
                        "title": "Compromiso de A",
                        "responsible": "Usuario A",
                        "due_date": "2026-10-16",
                    },
                    "extraction": {
                        "source_quote": "Haré esto mañana.",
                        "confidence": 0.95,
                        "priority_origin": "default",
                    },
                }
            ],
        }

        create_res = self.client.post(
            "/api/commitments",
            headers={
                "Authorization": f"Bearer {token_a}",
                "Idempotency-Key": str(uuid4()),
            },
            json=payload,
        )
        self.assertEqual(create_res.status_code, 201)
        item_id = create_res.json()["items"][0]["id"]

        # Usuario A puede ver su compromiso
        list_a = self.client.get(
            "/api/commitments",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        self.assertEqual(list_a.status_code, 200)
        self.assertEqual(list_a.json()["total"], 1)

        # Usuario B NO puede ver el compromiso de A
        list_b = self.client.get(
            "/api/commitments",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        self.assertEqual(list_b.status_code, 200)
        self.assertEqual(list_b.json()["total"], 0)

        # Usuario B intenta consultar directamente el compromiso de A
        get_b = self.client.get(
            f"/api/commitments/{item_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        self.assertEqual(get_b.status_code, 404)
