"""Disaster recovery — recovery plans, backup validation, and recovery drills.

Coordinates the backup + restore engines into an operational recovery posture:
ranks available backups, validates the latest recoverable point, runs a
non-destructive recovery simulation (restore into a scratch directory and
verify), and produces a recovery report with an overall readiness assessment.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

from .restore import RestoreEngine, RestoreError


class RecoveryManager:
    def __init__(self, backup_engine, restore_engine: RestoreEngine | None = None):
        self.backups = backup_engine
        self.restore = restore_engine or RestoreEngine(backup_engine)

    def recovery_points(self) -> list[dict]:
        """Available recovery points, newest first, with on-disk verification."""
        points = []
        for b in self.backups.list_backups(limit=10_000):
            v = self.backups.verify(b["backup_id"])
            points.append({"backup_id": b["backup_id"], "kind": b["kind"],
                           "created_at": b["created_at"], "size_bytes": b["size_bytes"],
                           "recoverable": v["valid"], "reason": v["reason"]})
        return points

    def recovery_plan(self) -> dict:
        """A concrete plan: latest full + incrementals after it, and target stores."""
        points = sorted(self.recovery_points(), key=lambda p: p["created_at"])
        fulls = [p for p in points if p["kind"] == "full" and p["recoverable"]]
        if not fulls:
            return {"ready": False, "reason": "no recoverable full backup", "steps": []}
        base = fulls[-1]
        incrementals = [p for p in points
                        if p["kind"] == "incremental" and p["recoverable"]
                        and p["created_at"] > base["created_at"]]
        steps = [{"order": 1, "action": "restore_full", "backup_id": base["backup_id"]}]
        for i, inc in enumerate(incrementals, start=2):
            steps.append({"order": i, "action": "apply_incremental", "backup_id": inc["backup_id"]})
        return {"ready": True, "base_backup": base["backup_id"],
                "incrementals": [p["backup_id"] for p in incrementals],
                "recovery_point": (incrementals[-1] if incrementals else base)["created_at"],
                "steps": steps}

    def validate_latest(self, password: str) -> dict:
        """Deep-validate the most recent backup (checksum + every member decrypts)."""
        backups = self.backups.list_backups(limit=1)
        if not backups:
            return {"valid": False, "reason": "no backups exist"}
        return self.restore.validate(backups[0]["backup_id"], password)

    def simulate_recovery(self, password: str) -> dict:
        """Non-destructive drill: restore the recovery plan into a scratch dir and
        confirm each target rebuilds with tables intact. Nothing live is touched."""
        plan = self.recovery_plan()
        if not plan["ready"]:
            return {"success": False, "reason": plan["reason"], "plan": plan}
        scratch = tempfile.mkdtemp(prefix="helios-dr-")
        try:
            as_of = plan["recovery_point"]
            base_rec = self.backups.get_record(plan["base_backup"])
            loaded = self.restore._load_archive(base_rec, password)
            names = list(loaded["archive"]["members"].keys())
            targets = {n: os.path.join(scratch, n + ".db") for n in names}
            result = self.restore.restore_point_in_time(password, as_of, targets)
            restored = result["restored"]
            healthy = {n: r["tables"] for n, r in restored.items()}
            return {"success": bool(restored), "recovery_point": as_of,
                    "restored_targets": len(restored), "tables_by_target": healthy,
                    "layers": result["layers"]}
        except RestoreError as exc:
            return {"success": False, "reason": str(exc)}
        finally:
            for f in os.listdir(scratch):
                try:
                    os.remove(os.path.join(scratch, f))
                except OSError:
                    pass
            os.rmdir(scratch)

    def report(self, password: str | None = None) -> dict:
        """Full recovery readiness report."""
        points = self.recovery_points()
        recoverable = [p for p in points if p["recoverable"]]
        plan = self.recovery_plan()
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_backups": len(points),
            "recoverable_backups": len(recoverable),
            "latest_recovery_point": recoverable[0]["created_at"] if recoverable else None,
            "plan_ready": plan["ready"],
            "plan": plan,
        }
        if password is not None:
            report["latest_validation"] = self.validate_latest(password)
            report["drill"] = self.simulate_recovery(password)
        report["readiness"] = (
            "ready" if plan["ready"] and recoverable else
            "degraded" if recoverable else "not_ready")
        return report
