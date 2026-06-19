"""PluginLoader — install/enable/disable/uninstall lifecycle over the registry."""
from __future__ import annotations

from typing import Optional

from .manifest import parse_manifest
from .registry import get_registry


class PluginLoader:
    def __init__(self):
        self._registry = get_registry()

    def install(self, manifest_data: dict, actor: Optional[str] = None) -> dict:
        manifest = parse_manifest(manifest_data)
        plugin = self._registry.register(manifest, actor=actor)
        return {"success": True, "plugin_id": plugin["id"], "manifest": manifest.to_dict()}

    def enable(self, plugin_id: str, actor: Optional[str] = None) -> dict:
        if not self._registry.get(plugin_id):
            return {"success": False, "error": "plugin not found"}
        ok = self._registry.set_status(plugin_id, "enabled", actor=actor)
        return {"success": ok, "plugin_id": plugin_id}

    def disable(self, plugin_id: str, actor: Optional[str] = None) -> dict:
        if not self._registry.get(plugin_id):
            return {"success": False, "error": "plugin not found"}
        ok = self._registry.set_status(plugin_id, "disabled", actor=actor)
        return {"success": ok, "plugin_id": plugin_id}

    def uninstall(self, plugin_id: str, actor: Optional[str] = None) -> dict:
        ok = self._registry.unregister(plugin_id, actor=actor)
        return {"success": ok, "plugin_id": plugin_id}

    def get_plugin_info(self, plugin_id: str) -> Optional[dict]:
        return self._registry.get(plugin_id)

    def list_installed(self) -> list[dict]:
        return self._registry.list()

    def refresh(self) -> dict:
        enabled = self._registry.list(status="enabled")
        return {"reloaded": len(enabled), "plugins": [p["id"] for p in enabled]}


_instance: Optional[PluginLoader] = None


def get_loader() -> PluginLoader:
    global _instance
    if _instance is None:
        _instance = PluginLoader()
    return _instance
