"""Entry point for the bundled HELIOS backend (PyInstaller target).

The standalone HELIOS desktop app ships this as a native binary and launches it
instead of requiring a system Python install. It simply runs the FastAPI app
with uvicorn on localhost; the Electron shell talks to it over HTTP exactly as
it would the dev sidecar.
"""
from __future__ import annotations

import os


def main() -> None:
    import uvicorn
    from app.main import app

    port = int(os.environ.get("HELIOS_SIDECAR_PORT", "8420"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
