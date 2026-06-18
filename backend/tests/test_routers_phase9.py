"""API tests for the Phase-9 security / vault / backup / recovery / sync routes."""
import unittest

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class SecurityRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client.post("/platform/coa/seed", params={"template": "general_small_business"})
        # Initialize + unlock the vault for the encrypted/sync surfaces.
        if not client.get("/security/status").json()["vault"]["initialized"]:
            client.post("/security/initialize", json={"master_password": "api-master-pw"})

    def test_status_and_health(self):
        st = client.get("/security/status").json()
        self.assertEqual(st["vault"]["algorithm"], "AES-256-GCM")
        self.assertTrue(st["compliance"]["chain"]["valid"])
        h = client.get("/security/health").json()
        self.assertIn(h["status"], ("healthy", "degraded"))
        self.assertIn("vault", h["stores"])

    def test_vault_secret_roundtrip(self):
        r = client.post("/vault/secret", json={"ref": "smtp:password", "value": "s3cr3t", "category": "email"})
        self.assertEqual(r.status_code, 200)
        got = client.get("/vault/secret/smtp:password").json()
        self.assertEqual(got["value"], "s3cr3t")
        # listing exposes metadata only
        listing = client.get("/vault/secrets").json()["secrets"]
        self.assertTrue(any(s["ref"] == "smtp:password" for s in listing))
        self.assertNotIn("s3cr3t", str(listing))

    def test_encrypted_memory_and_documents(self):
        client.post("/security/memory", json={"key": "pref:tone", "value": {"tone": "concise"}})
        self.assertEqual(client.get("/security/memory/pref:tone").json()["value"], {"tone": "concise"})
        client.post("/security/document", json={"doc_id": "rpt:q1", "payload": {"net_income": 1000}})
        self.assertEqual(client.get("/security/document/rpt:q1").json()["value"], {"net_income": 1000})

    def test_compliance_and_permissions(self):
        client.post("/compliance/record", json={"category": "admin", "action": "test_event"})
        self.assertTrue(client.get("/compliance/verify").json()["valid"])
        perms = client.get("/security/permissions/accounting").json()
        self.assertFalse(perms["can_approve"])

    def test_integrity_scan(self):
        # post a balanced entry via the platform, then verify integrity
        client.post("/platform/journal", json={
            "date": "2026-02-01", "memo": "integrity check",
            "lines": [{"account": "1000", "debit": 100}, {"account": "4000", "credit": 100}]})
        led = client.get("/security/integrity/ledger").json()
        self.assertTrue(led["valid"])
        aud = client.get("/security/integrity/audit").json()
        self.assertTrue(aud["valid"])

    def test_backup_restore_recovery_cycle(self):
        b = client.post("/backup/create", json={"password": "bk-pw", "kind": "full"}).json()
        self.assertIn("backup_id", b)
        self.assertTrue(client.get(f"/backup/{b['backup_id']}/verify").json()["valid"])
        self.assertTrue(client.post("/restore/validate",
                                    json={"backup_id": b["backup_id"], "password": "bk-pw"}).json()["valid"])
        plan = client.get("/recovery/plan").json()
        self.assertTrue(plan["ready"])
        drill = client.post("/recovery/simulate", json={"password": "bk-pw"}).json()
        self.assertTrue(drill["success"])

    def test_sync_devices_and_delta(self):
        laptop = client.post("/sync/device", json={"name": "laptop"}).json()["device_id"]
        phone = client.post("/sync/device", json={"name": "phone"}).json()["device_id"]
        client.post("/sync/push", json={"device_id": laptop,
                                        "changes": [{"key": "n:1", "value": {"t": "hi"}, "base_version": 0}]})
        pulled = client.post("/sync/pull", json={"device_id": phone}).json()
        self.assertTrue(any(c["value"] == {"t": "hi"} for c in pulled["changes"]))
        self.assertEqual(client.get("/sync/status").json()["algorithm"], "AES-256-GCM")

    def test_locked_vault_blocks_sync(self):
        client.post("/security/lock")
        self.assertEqual(client.get("/sync/status").status_code, 423)
        client.post("/security/unlock", json={"master_password": "api-master-pw"})


if __name__ == "__main__":
    unittest.main()
