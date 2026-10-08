from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.database import Database
from backend.app.main import create_app
from scripts.import_synthea import seed_demo_patients


class APITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="pramanrx-test-")
        root = Path(self.tempdir.name)
        compiled = PROJECT_ROOT / "data/compiled"
        for name in ("kb-v1.json", "kb-v1.sig", "pramanrx-ed25519-public.pem"):
            shutil.copy2(compiled / name, root / name)
        shutil.copy2(PROJECT_ROOT / "data/runtime/pramanrx-ed25519-private.pem", root / "private.pem")
        self.settings = Settings(
            database_path=root / "test.sqlite3", kb_path=root / "kb-v1.json",
            kb_signature_path=root / "kb-v1.sig", public_key_path=root / "pramanrx-ed25519-public.pem",
            private_key_path=root / "private.pem", ollama_url="http://127.0.0.1:1",
            external_ai_url=None, external_ai_token=None,
        )
        db = Database(self.settings.database_path)
        db.initialize()
        seed_demo_patients(db)
        self.client_context = TestClient(create_app(self.settings))
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_health_and_kb_status(self) -> None:
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["kb_verified"])
        status = self.client.get("/api/v1/kb/status").json()
        self.assertTrue(status["verified"])
        self.assertEqual(status["version"], "2026.10.06-prototype.1")

    def test_patient_and_fhir_projection(self) -> None:
        patients = self.client.get("/api/v1/patients", params={"q": "Pregnancy"}).json()["items"]
        self.assertEqual(patients[0]["id"], "demo-pregnancy")
        fhir = self.client.get("/fhir/Patient/demo-pregnancy").json()
        self.assertEqual(fhir["resourceType"], "Patient")
        self.assertEqual(fhir["gender"], "female")
        context = self.client.get("/api/v1/patients/demo-pregnancy/context").json()
        self.assertEqual(context["trust"], "authoritative_synthetic_record")
        self.assertEqual(context["conditions"][0]["description"], "Pregnancy")

    def test_deterministic_ai_gets_no_patient_context(self) -> None:
        response = self.client.post("/api/v1/ai/generate", json={
            "adapter": "deterministic", "prompt": "Suggest ibuprofen for a headache",
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["trust"], "untrusted")
        self.assertFalse(body["authoritative_patient_context_shared"])
        self.assertEqual(body["context_disclosure"], [])

    def test_external_adapter_is_disabled_by_default(self) -> None:
        response = self.client.post("/api/v1/ai/generate", json={"adapter": "external", "prompt": "test"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"]["code"], "ADAPTER_ERROR")

    def test_all_documented_scenarios(self) -> None:
        scenarios = self.client.get("/api/v1/scenarios").json()["items"]
        self.assertGreaterEqual(len(scenarios), 7)
        for scenario in scenarios:
            with self.subTest(scenario=scenario["id"]):
                response = self.client.post(f"/api/v1/scenarios/{scenario['id']}/run")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["verdict"], scenario["expected_verdict"])
                if not scenario.get("simulation"):
                    self.assertEqual(response.json()["ai_trust"], "untrusted")

    def test_unknown_medication_requires_manual_review(self) -> None:
        response = self.client.post("/api/v1/evaluations", json={
            "patient_id": "demo-clear", "ai_response": "Use mysterydrug 20 mg daily.",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["verdict"], "insufficient_context")

    def test_patient_creation_and_system_surfaces(self) -> None:
        created = self.client.post("/api/v1/patients", json={
            "first_name": "Taylor", "last_name": "Synthetic", "birth_date": "1990-01-01",
            "gender": "X", "race": "declined", "ethnicity": "declined",
        })
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["source"], "user_created_synthetic")
        self.assertGreaterEqual(len(self.client.get("/api/v1/adapters").json()["items"]), 4)
        self.assertEqual(self.client.get("/api/v1/system/status").json()["knowledge_base"], "verified")
        self.assertTrue(self.client.post("/api/v1/kb/verify").json()["verified"])

    def test_action_and_audit_chain(self) -> None:
        evaluation = self.client.post("/api/v1/evaluations", json={
            "patient_id": "demo-warfarin", "ai_response": "Use ibuprofen 400 mg twice daily.",
        }).json()
        action = self.client.post(
            f"/api/v1/evaluations/{evaluation['evaluation_id']}/actions",
            json={"action": "override", "actor": "Dr Test", "reason": "Documented demo review"},
        )
        self.assertEqual(action.status_code, 201)
        verification = self.client.get("/api/v1/audit/verify").json()
        self.assertTrue(verification["valid"], verification["errors"])
        self.assertEqual(verification["records"], 2)

    def test_audit_tampering_is_detected(self) -> None:
        evaluation = self.client.post("/api/v1/evaluations", json={
            "patient_id": "demo-clear", "ai_response": "Use acetaminophen 500 mg once.",
        }).json()
        with Database(self.settings.database_path).connect() as connection:
            connection.execute(
                "UPDATE evaluations SET result_json=? WHERE id=?", ("{}", evaluation["evaluation_id"])
            )
        verification = self.client.get("/api/v1/audit/verify").json()
        self.assertFalse(verification["valid"])
        self.assertIn("content hash mismatch", verification["errors"][0])


class FailClosedTestCase(unittest.TestCase):
    def test_tampered_kb_disables_evaluations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pramanrx-kb-tamper-") as raw:
            root = Path(raw)
            kb = root / "kb.json"
            kb.write_bytes((PROJECT_ROOT / "data/compiled/kb-v1.json").read_bytes() + b" ")
            shutil.copy2(PROJECT_ROOT / "data/compiled/kb-v1.sig", root / "kb.sig")
            shutil.copy2(PROJECT_ROOT / "data/compiled/pramanrx-ed25519-public.pem", root / "public.pem")
            shutil.copy2(PROJECT_ROOT / "data/runtime/pramanrx-ed25519-private.pem", root / "private.pem")
            settings = Settings(
                database_path=root / "db.sqlite", kb_path=kb, kb_signature_path=root / "kb.sig",
                public_key_path=root / "public.pem", private_key_path=root / "private.pem",
            )
            db = Database(settings.database_path)
            db.initialize()
            seed_demo_patients(db)
            with TestClient(create_app(settings)) as client:
                self.assertEqual(client.get("/health").json()["status"], "degraded")
                response = client.post("/api/v1/evaluations", json={
                    "patient_id": "demo-clear", "ai_response": "acetaminophen 500 mg",
                })
                self.assertEqual(response.status_code, 503)
                self.assertTrue(response.json()["detail"]["fail_closed"])


if __name__ == "__main__":
    unittest.main()
