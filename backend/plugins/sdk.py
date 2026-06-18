"""HELIOS Plugin SDK — base classes and sandboxed context for plugin authors."""
from __future__ import annotations

from typing import Any, List

from .manifest import PluginManifest


class HeliosPlugin:
    """Base class for all HELIOS plugins."""

    manifest: PluginManifest

    def on_install(self) -> None:
        pass

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def on_uninstall(self) -> None:
        pass


class ToolPlugin(HeliosPlugin):
    """Plugin that adds tools/commands to HELIOS."""

    def get_tools(self) -> List[dict]:
        return []  # list of {name, description, handler}


class DataPlugin(HeliosPlugin):
    """Plugin that adds data sources."""

    def get_schema(self) -> dict:
        return {}

    def query(self, params: dict) -> Any:
        raise NotImplementedError


class UIPlugin(HeliosPlugin):
    """Plugin that adds UI views."""

    def get_views(self) -> List[dict]:
        return []  # list of {id, label, icon, component_path}


class PluginContext:
    """Sandboxed context passed to plugins — gates access to host capabilities."""

    def __init__(self, plugin_id: str, permissions: List[str]):
        self.plugin_id = plugin_id
        self.permissions = set(permissions)
        self._log_buffer: List[str] = []

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str) -> None:
        if not self.has_permission(permission):
            raise PermissionError(f"Plugin '{self.plugin_id}' lacks permission: {permission}")

    def get_accounting_summary(self) -> dict:
        self.require("accounting:read")
        try:
            from accounting.service import AccountingService  # type: ignore
            return {"available": True, "source": "accounting.service"}
        except Exception:
            return {"available": False, "note": "accounting subsystem not loaded"}

    def log(self, message: str) -> None:
        self._log_buffer.append(message)

    def get_logs(self) -> List[str]:
        return list(self._log_buffer)
