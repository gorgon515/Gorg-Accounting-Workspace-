"""Sidecar configuration. Localhost-only by default; overridable via env."""
from __future__ import annotations

import os

VERSION = "0.2.0"
SERVICE = "helios-intelligence-sidecar"

# Bound to loopback — the sidecar must never be reachable off-box.
HOST = os.environ.get("HELIOS_SIDECAR_HOST", "127.0.0.1")
PORT = int(os.environ.get("HELIOS_SIDECAR_PORT", "8420"))

# The Electron app passes its renderer origin; we only allow localhost origins.
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "app://.",  # Electron file origin
]
