"""PluginSandbox — permission-gated plugin execution with audit logging."""
from __future__ import annotations

from typing import Optional

from .registry import get_connection, _now


class PluginSandbox:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def _conn(self):
        return get_connection(self._db_path)

    def check_permissions(self, requested: list[str], granted: list[str]) -> dict:
        granted_set = set(granted)
        allowed = [p for p in requested if p in granted_set]
        blocked = [p for p in requested if p not in granted_set]
        return {"allowed": allowed, "blocked": blocked}

    def execute(self, plugin_id: str, function_name: str, args: Optional[dict],
                permissions: list[str]) -> dict:
        """Run a declared plugin function within its granted permission set.

        The host does not exec arbitrary code here; it validates the call against the
        plugin's granted permissions, records it, and returns a structured result that
        the loader/registry can act on. Real handler dispatch happens in the loader for
        registered, enabled plugins.
        """
        from .registry import get_registry
        plugin = get_registry().get(plugin_id)
        if not plugin:
            self.audit_call(plugin_id, function_name, False, str(args), "plugin not found")
            return {"result": None, "allowed": False, "blocked_reason": "plugin not found"}
        if plugin["status"] != "enabled":
            self.audit_call(plugin_id, function_name, False, str(args), "plugin not enabled")
            return {"result": None, "allowed": False, "blocked_reason": "plugin not enabled"}
        granted = plugin["permissions"]
        check = self.check_permissions(permissions or [], granted)
        if check["blocked"]:
            reason = f"missing permissions: {check['blocked']}"
            self.audit_call(plugin_id, function_name, False, str(args), reason)
            return {"result": None, "allowed": False, "blocked_reason": reason}
        self.audit_call(plugin_id, function_name, True, str(args), None)
        return {
            "result": {"plugin_id": plugin_id, "function": function_name,
                       "executed": True, "permissions_used": check["allowed"]},
            "allowed": True,
            "blocked_reason": None,
        }

    def audit_call(self, plugin_id: str, function_name: str, allowed: bool,
                   args_summary: Optional[str], blocked_reason: Optional[str]) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO plugin_call_audit (plugin_id, function_name, allowed, args_summary, "
                "blocked_reason, created_at) VALUES (?,?,?,?,?,?)",
                (plugin_id, function_name, 1 if allowed else 0,
                 (args_summary or "")[:500], blocked_reason, _now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_audit_log(self, plugin_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        conn = self._conn()
        try:
            if plugin_id:
                rows = conn.execute(
                    "SELECT * FROM plugin_call_audit WHERE plugin_id=? ORDER BY created_at DESC LIMIT ?",
                    (plugin_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM plugin_call_audit ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["allowed"] = bool(d["allowed"])
                out.append(d)
            return out
        finally:
            conn.close()


_instance: Optional[PluginSandbox] = None


def get_sandbox() -> PluginSandbox:
    global _instance
    if _instance is None:
        _instance = PluginSandbox()
    return _instance
