"""Plugin manifest parsing and validation."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

REQUIRED_FIELDS = ["name", "version", "description", "author", "entry_point", "permissions"]

ALLOWED_PERMISSIONS = [
    "accounting:read", "accounting:write", "vault:read", "memory:read",
    "memory:write", "reports:read", "network:outbound", "filesystem:read",
    "filesystem:write", "sidecar:call", "ui:render",
]

_SEMVER = re.compile(r"^\d+\.\d+\.\d+([-+].+)?$")


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    permissions: List[str]
    min_helios_version: str = "0.8.0"
    max_helios_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    license: str = "MIT"

    def to_dict(self) -> dict:
        return {
            "name": self.name, "version": self.version, "description": self.description,
            "author": self.author, "entry_point": self.entry_point,
            "permissions": self.permissions, "min_helios_version": self.min_helios_version,
            "max_helios_version": self.max_helios_version, "tags": self.tags,
            "homepage": self.homepage, "license": self.license,
        }


def parse_manifest(data: dict) -> PluginManifest:
    missing = [f for f in REQUIRED_FIELDS if f not in data or data[f] in (None, "")]
    if missing:
        raise ValueError(f"Manifest missing required fields: {missing}")
    if not _SEMVER.match(str(data["version"])):
        raise ValueError(f"Invalid version (expected semver X.Y.Z): {data['version']}")
    perms = data["permissions"]
    if not isinstance(perms, list):
        raise ValueError("permissions must be a list")
    invalid = [p for p in perms if p not in ALLOWED_PERMISSIONS]
    if invalid:
        raise ValueError(f"Unknown permissions: {invalid}")
    return PluginManifest(
        name=data["name"], version=data["version"], description=data["description"],
        author=data["author"], entry_point=data["entry_point"], permissions=list(perms),
        min_helios_version=data.get("min_helios_version", "0.8.0"),
        max_helios_version=data.get("max_helios_version"),
        tags=list(data.get("tags", [])), homepage=data.get("homepage"),
        license=data.get("license", "MIT"),
    )


def load_manifest_file(path: str) -> PluginManifest:
    with open(path, "r", encoding="utf-8") as f:
        return parse_manifest(json.load(f))
