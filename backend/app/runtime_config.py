"""Runtime secrets/config bootstrap for the HELIOS sidecar.

A packaged desktop app (double-clicked, not launched from a shell) does NOT
inherit the user's exported environment variables — on macOS especially, a GUI
launch gets a minimal environment. That means integration keys set in a shell
profile never reach the bundled sidecar.

To make API keys reach the sidecar regardless of how the app was launched, this
module loads a small JSON config from a stable, user-editable location at
startup and merges it into ``os.environ`` (without clobbering values that are
already set — explicit env vars still win).

Lookup order (first existing file wins, but all are merged, later files do not
override earlier non-empty values):

  1. $HELIOS_CONFIG_FILE                          (explicit override)
  2. ~/.helios/config.json                        (primary user-editable home)
  3. <dir of the running binary>/helios.config.json

The file is a flat ``{"ENV_VAR": "value"}`` JSON map, e.g.::

    {
      "TRADINGVIEW_RAPIDAPI_KEY": "…",
      "ELEVENLABS_API_KEY": "…",
      "ROBINHOOD_USERNAME": "you@example.com",
      "ROBINHOOD_PASSWORD": "…"
    }
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

# The integration keys HELIOS knows how to surface in the Settings UI. Listed
# here so the settings API can report configured/missing status consistently.
KNOWN_KEYS: List[str] = [
    "TRADINGVIEW_RAPIDAPI_KEY",
    "ELEVENLABS_API_KEY",
    "ROBINHOOD_USERNAME",
    "ROBINHOOD_PASSWORD",
    "ROBINHOOD_MFA_CODE",
    "ANTHROPIC_API_KEY",
]

# Keys that are secret and must be masked when their status is reported.
SECRET_KEYS = {
    "TRADINGVIEW_RAPIDAPI_KEY",
    "ELEVENLABS_API_KEY",
    "ROBINHOOD_PASSWORD",
    "ROBINHOOD_MFA_CODE",
    "ANTHROPIC_API_KEY",
}


def config_home() -> Path:
    """The primary user-editable config directory (~/.helios)."""
    return Path(os.path.expanduser("~")) / ".helios"


def config_path() -> Path:
    """The primary config file path (~/.helios/config.json)."""
    explicit = os.environ.get("HELIOS_CONFIG_FILE")
    if explicit:
        return Path(explicit)
    return config_home() / "config.json"


def _candidate_paths() -> List[Path]:
    paths: List[Path] = []
    explicit = os.environ.get("HELIOS_CONFIG_FILE")
    if explicit:
        paths.append(Path(explicit))
    paths.append(config_home() / "config.json")
    # Next to the running binary (frozen bundle) or this file (dev).
    try:
        base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        paths.append(base / "helios.config.json")
    except Exception:
        pass
    return paths


def _read(path: Path) -> Dict[str, str]:
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items() if v is not None and str(v) != ""}
    except Exception:
        pass
    return {}


def load_into_environ() -> Dict[str, bool]:
    """Merge config-file values into os.environ.

    Explicit, already-present env vars win (they are not overwritten). Returns a
    map of {key: was_applied} for the keys that came from a config file.
    """
    applied: Dict[str, bool] = {}
    for path in _candidate_paths():
        for key, value in _read(path).items():
            if not os.environ.get(key):  # don't clobber an explicit env var
                os.environ[key] = value
                applied[key] = True
    return applied


def current_values() -> Dict[str, str]:
    """Read the on-disk config map from the primary path (unmerged)."""
    return _read(config_path())


def save_values(updates: Dict[str, str]) -> Dict[str, str]:
    """Persist key/value updates to ~/.helios/config.json and apply them live.

    An empty-string value deletes the key. Returns the resulting on-disk map.
    Also updates os.environ immediately so changes take effect without a
    sidecar restart.
    """
    home = config_home()
    home.mkdir(parents=True, exist_ok=True)
    path = config_path()
    existing = _read(path)

    for key, value in updates.items():
        key = str(key)
        if value is None or str(value) == "":
            existing.pop(key, None)
            os.environ.pop(key, None)
        else:
            existing[key] = str(value)
            os.environ[key] = str(value)

    path.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")
    try:  # tighten permissions — this file holds secrets
        os.chmod(path, 0o600)
    except Exception:
        pass
    return existing


def status() -> Dict[str, Dict[str, object]]:
    """Configured/missing status for every known key, with secrets masked."""
    out: Dict[str, Dict[str, object]] = {}
    for key in KNOWN_KEYS:
        val = os.environ.get(key, "")
        configured = bool(val)
        hint = ""
        if configured:
            if key in SECRET_KEYS:
                hint = ("•" * max(0, len(val) - 4)) + val[-4:] if len(val) > 4 else "••••"
            else:
                hint = val
        out[key] = {"configured": configured, "hint": hint, "secret": key in SECRET_KEYS}
    return out
