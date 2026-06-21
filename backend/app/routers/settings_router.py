"""Settings API — integration keys for HELIOS.

Lets the desktop UI inspect which integration keys are configured (status only,
secrets masked) and write new values to the user-editable config file
(~/.helios/config.json). Saved values are applied to the running process
immediately, so newly entered keys take effect without restarting the sidecar.
"""
from __future__ import annotations

from typing import Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])


class KeysBody(BaseModel):
    # Flat map of {ENV_VAR: value}. Empty string deletes the key. Unknown keys
    # are accepted too, so future integrations don't need a schema change.
    keys: Dict[str, str]


@router.get("/keys")
def get_keys():
    """Configured/missing status for every known integration key (masked)."""
    from app.runtime_config import status, config_path
    return {"status": status(), "config_file": str(config_path())}


@router.post("/keys")
def set_keys(body: KeysBody):
    """Persist + apply integration keys. Returns refreshed (masked) status."""
    from app.runtime_config import save_values, status, config_path

    save_values(body.keys)

    # If Robinhood credentials changed, drop the cached login so the next call
    # re-authenticates with the new values.
    if any(k.startswith("ROBINHOOD_") for k in body.keys):
        try:
            import market_data.robinhood as rh
            rh._logged_in = False  # type: ignore[attr-defined]
        except Exception:
            pass

    return {"status": status(), "config_file": str(config_path()), "saved": True}


@router.get("/integrations")
def integrations():
    """High-level readiness of each integration the UI can show as a badge."""
    import os
    tv = bool(os.environ.get("TRADINGVIEW_RAPIDAPI_KEY"))
    el = bool(os.environ.get("ELEVENLABS_API_KEY"))
    rh = bool(os.environ.get("ROBINHOOD_USERNAME") and os.environ.get("ROBINHOOD_PASSWORD"))
    return {
        "tradingview": {"configured": tv, "keys": ["TRADINGVIEW_RAPIDAPI_KEY"]},
        "elevenlabs": {"configured": el, "keys": ["ELEVENLABS_API_KEY"]},
        "robinhood": {"configured": rh, "keys": ["ROBINHOOD_USERNAME", "ROBINHOOD_PASSWORD", "ROBINHOOD_MFA_CODE"]},
    }
