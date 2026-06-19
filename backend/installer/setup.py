"""SetupManager — first-run data directory, migrations, config, and verification."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
_SUBDIRS = ["backups", "enc_docs", "enc_memory", "vault", "updates"]
_CONFIG_FILE = os.path.join(BASE_DIR, "helios_config.json")

try:
    from app.config import VERSION
except Exception:  # pragma: no cover
    VERSION = "0.8.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SetupManager:
    def initialize_data_directory(self, data_dir: Optional[str] = None) -> dict:
        d = data_dir or BASE_DIR
        created = []
        os.makedirs(d, exist_ok=True)
        for sub in _SUBDIRS:
            path = os.path.join(d, sub)
            if not os.path.isdir(path):
                os.makedirs(path, exist_ok=True)
                created.append(sub)
        return {"success": True, "data_dir": d, "created_dirs": created}

    def run_database_migrations(self) -> dict:
        details = []
        # Each subsystem creates its schema lazily on first connection; touching them
        # here makes installation deterministic.
        try:
            from workspaces.db import get_connection as wsc
            wsc().close()
            details.append("workspaces.db")
        except Exception as e:
            details.append(f"workspaces: {e}")
        try:
            from monitoring.db import get_connection as mc
            mc().close()
            details.append("monitoring.db")
        except Exception as e:
            details.append(f"monitoring: {e}")
        try:
            from public_api.db import get_connection as pc
            pc().close()
            details.append("public_api.db")
        except Exception as e:
            details.append(f"public_api: {e}")
        try:
            from plugins.registry import get_connection as gc
            gc().close()
            details.append("plugins.db")
        except Exception as e:
            details.append(f"plugins: {e}")
        return {"success": True, "migrations_run": len(details), "details": details}

    def create_default_config(self) -> dict:
        settings = {
            "version": VERSION, "host": "127.0.0.1", "port": 8420,
            "channel": "stable", "telemetry": False, "created_at": _now(),
        }
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return {"success": True, "config_path": _CONFIG_FILE, "settings": settings}

    def verify_installation(self) -> dict:
        checks_passed, checks_failed, details = 0, 0, []
        # Data dir
        if os.path.isdir(BASE_DIR):
            checks_passed += 1
            details.append("data directory present")
        else:
            checks_failed += 1
            details.append("data directory missing")
        # Subdirs
        for sub in _SUBDIRS:
            if os.path.isdir(os.path.join(BASE_DIR, sub)):
                checks_passed += 1
            else:
                checks_failed += 1
                details.append(f"missing subdir: {sub}")
        # Config
        if os.path.isfile(_CONFIG_FILE):
            checks_passed += 1
            details.append("config present")
        else:
            checks_failed += 1
            details.append("config missing")
        return {"valid": checks_failed == 0, "checks_passed": checks_passed,
                "checks_failed": checks_failed, "details": details}

    def get_installation_info(self) -> dict:
        installed_at = None
        status = "not_installed"
        if os.path.isfile(_CONFIG_FILE):
            try:
                with open(_CONFIG_FILE, encoding="utf-8") as f:
                    installed_at = json.load(f).get("created_at")
                status = "installed"
            except Exception:
                pass
        return {"version": VERSION, "data_dir": BASE_DIR, "config_file": _CONFIG_FILE,
                "installed_at": installed_at, "status": status}


_instance: Optional[SetupManager] = None


def get_setup_manager() -> SetupManager:
    global _instance
    if _instance is None:
        _instance = SetupManager()
    return _instance
