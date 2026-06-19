"""InstallValidator — preflight environment checks for HELIOS installation."""
from __future__ import annotations

import importlib.util
import os
import shutil
import socket
import sys
from typing import Optional

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
_REQUIRED_PACKAGES = ["fastapi", "uvicorn", "pydantic", "cryptography"]
_MIN_PYTHON = (3, 10)


class InstallValidator:
    def check_python_version(self) -> dict:
        v = sys.version_info
        ok = (v.major, v.minor) >= _MIN_PYTHON
        return {"ok": ok, "version": f"{v.major}.{v.minor}.{v.micro}",
                "required": f">={_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}"}

    def check_dependencies(self) -> dict:
        installed, missing = [], []
        for pkg in _REQUIRED_PACKAGES:
            if importlib.util.find_spec(pkg) is not None:
                installed.append(pkg)
            else:
                missing.append(pkg)
        return {"ok": not missing, "installed": installed, "missing": missing}

    def check_disk_space(self, required_mb: int = 500) -> dict:
        try:
            usage = shutil.disk_usage(os.path.dirname(BASE_DIR) or ".")
            available_mb = usage.free // (1024 * 1024)
        except Exception:
            available_mb = 0
        return {"ok": available_mb >= required_mb, "available_mb": available_mb,
                "required_mb": required_mb}

    def check_ports(self, ports: Optional[list[int]] = None) -> dict:
        ports = ports or [8420]
        available, in_use = [], []
        for port in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            try:
                result = s.connect_ex(("127.0.0.1", port))
                (available if result != 0 else in_use).append(port)
            finally:
                s.close()
        return {"ok": True, "available": available, "in_use": in_use}

    def check_database_access(self, data_dir: Optional[str] = None) -> dict:
        d = data_dir or BASE_DIR
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".write_probe")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
            writable = True
        except Exception:
            writable = False
        return {"ok": writable, "data_dir": d, "writable": writable}

    def run_all(self) -> dict:
        checks = {
            "python_version": self.check_python_version(),
            "dependencies": self.check_dependencies(),
            "disk_space": self.check_disk_space(),
            "ports": self.check_ports(),
            "database_access": self.check_database_access(),
        }
        passed = all(c.get("ok") for c in checks.values())
        return {"passed": passed, "checks": checks}


_instance: Optional[InstallValidator] = None


def get_validator() -> InstallValidator:
    global _instance
    if _instance is None:
        _instance = InstallValidator()
    return _instance
