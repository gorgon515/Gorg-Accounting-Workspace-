"""Update channels for the HELIOS auto-updater."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UpdateChannel:
    name: str
    description: str
    stability: str  # "stable", "beta", "dev"
    auto_download: bool
    auto_install: bool
    latest_version: str


CHANNELS = {
    "stable": UpdateChannel("stable", "Production-tested releases", "stable", True, False, "0.9.0"),
    "beta": UpdateChannel("beta", "Pre-release features", "beta", True, False, "0.10.0-beta.1"),
    "dev": UpdateChannel("dev", "Nightly development builds", "dev", False, False, "0.11.0-dev.1"),
}


def get_channel(name: str) -> UpdateChannel:
    if name not in CHANNELS:
        raise ValueError(f"Unknown channel: {name}")
    return CHANNELS[name]


def list_channels() -> list[dict]:
    return [
        {
            "name": c.name, "description": c.description, "stability": c.stability,
            "auto_download": c.auto_download, "auto_install": c.auto_install,
            "latest_version": c.latest_version,
        }
        for c in CHANNELS.values()
    ]
