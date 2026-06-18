"""HELIOS Health Monitor API — /health-monitor endpoints."""
from __future__ import annotations

import os
from fastapi import APIRouter

router = APIRouter(prefix="/health-monitor", tags=["health-monitor"])

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(os.path.dirname(_HERE))
DATA_DIR = os.path.join(_BACKEND, ".data")


def _monitor():
    from health.monitor import get_monitor
    return get_monitor()


def _reporter():
    from health.reporter import HealthReporter
    return HealthReporter()


@router.get("/status")
def health_status() -> dict:
    try:
        return _monitor().check_all()
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/database")
def health_database() -> dict:
    try:
        m = _monitor()
        dbs = {
            "accounting": os.path.join(DATA_DIR, "accounting.db"),
            "intel": os.path.join(DATA_DIR, "intel.db"),
            "vault": os.path.join(DATA_DIR, "vault", "vault.db"),
            "compliance": os.path.join(DATA_DIR, "compliance.db"),
            "memory": os.path.join(DATA_DIR, "enc_memory", "memory.db"),
            "backup_catalog": os.path.join(DATA_DIR, "backups", "catalog.db"),
            "sync": os.path.join(DATA_DIR, "sync", "sync.db"),
            "health_log": os.path.join(DATA_DIR, "health_log.db"),
        }
        return {name: m.check_database(path) for name, path in dbs.items()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/security")
def health_security() -> dict:
    try:
        m = _monitor()
        return {
            "vault": m.check_vault(),
            "compliance_db": m.check_database(os.path.join(DATA_DIR, "compliance.db")),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/backup")
def health_backup() -> dict:
    try:
        return _monitor().check_backup_health()
    except Exception as e:
        return {"error": str(e)}


@router.get("/sync")
def health_sync() -> dict:
    try:
        return _monitor().check_sync_health()
    except Exception as e:
        return {"error": str(e)}


@router.get("/report/daily")
def daily_report() -> dict:
    try:
        return _reporter().daily_report()
    except Exception as e:
        return {"error": str(e)}


@router.get("/report/weekly")
def weekly_report() -> dict:
    try:
        return _reporter().weekly_report()
    except Exception as e:
        return {"error": str(e)}


@router.get("/history")
def health_history(days: int = 7) -> dict:
    try:
        return {"history": _reporter().get_health_history(days)}
    except Exception as e:
        return {"error": str(e)}
