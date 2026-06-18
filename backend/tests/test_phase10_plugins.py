"""Phase 10 — Plugin architecture tests."""
from __future__ import annotations

import pytest


def _manifest(**overrides):
    base = {
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "author": "tester",
        "entry_point": "main.py",
        "permissions": ["accounting:read"],
    }
    base.update(overrides)
    return base


def test_manifest_parse_valid():
    from plugins.manifest import parse_manifest
    m = parse_manifest(_manifest())
    assert m.name == "Test Plugin"
    assert m.permissions == ["accounting:read"]


def test_manifest_invalid_permission():
    from plugins.manifest import parse_manifest
    with pytest.raises(ValueError):
        parse_manifest(_manifest(permissions=["root:everything"]))


def test_manifest_missing_field():
    from plugins.manifest import parse_manifest
    bad = _manifest()
    del bad["author"]
    with pytest.raises(ValueError):
        parse_manifest(bad)


def test_manifest_bad_version():
    from plugins.manifest import parse_manifest
    with pytest.raises(ValueError):
        parse_manifest(_manifest(version="not-semver"))


def test_plugin_register(tmp_path):
    from plugins.registry import PluginRegistry
    from plugins.manifest import parse_manifest
    reg = PluginRegistry(str(tmp_path / "plugins.db"))
    p = reg.register(parse_manifest(_manifest()))
    assert p["id"] == "test-plugin"
    assert p["status"] == "installed"


def test_plugin_lifecycle(tmp_path, monkeypatch):
    import plugins.registry as registry_mod
    reg = registry_mod.PluginRegistry(str(tmp_path / "plugins.db"))
    monkeypatch.setattr(registry_mod, "_instance", reg)
    from plugins.loader import PluginLoader
    loader = PluginLoader()
    loader._registry = reg
    res = loader.install(_manifest())
    pid = res["plugin_id"]
    assert loader.enable(pid)["success"] is True
    assert reg.get(pid)["status"] == "enabled"
    assert loader.disable(pid)["success"] is True
    assert reg.get(pid)["status"] == "disabled"
    assert loader.uninstall(pid)["success"] is True
    assert reg.get(pid) is None


def test_plugin_list_by_status(tmp_path):
    from plugins.registry import PluginRegistry
    from plugins.manifest import parse_manifest
    reg = PluginRegistry(str(tmp_path / "plugins.db"))
    reg.register(parse_manifest(_manifest(name="Plugin A")))
    b = reg.register(parse_manifest(_manifest(name="Plugin B")))
    reg.set_status(b["id"], "enabled")
    enabled = reg.list(status="enabled")
    assert len(enabled) == 1
    assert enabled[0]["id"] == "plugin-b"


def test_sandbox_permission_check(tmp_path):
    from plugins.sandbox import PluginSandbox
    sb = PluginSandbox(str(tmp_path / "plugins.db"))
    result = sb.check_permissions(["accounting:read", "vault:read"], ["accounting:read"])
    assert result["allowed"] == ["accounting:read"]
    assert result["blocked"] == ["vault:read"]


def test_sandbox_audit_log(tmp_path, monkeypatch):
    import plugins.registry as registry_mod
    reg = registry_mod.PluginRegistry(str(tmp_path / "plugins.db"))
    monkeypatch.setattr(registry_mod, "_instance", reg)
    from plugins.manifest import parse_manifest
    p = reg.register(parse_manifest(_manifest()))
    reg.set_status(p["id"], "enabled")
    from plugins.sandbox import PluginSandbox
    sb = PluginSandbox(str(tmp_path / "plugins.db"))
    out = sb.execute(p["id"], "do_thing", {"x": 1}, ["accounting:read"])
    assert out["allowed"] is True
    log = sb.get_audit_log(p["id"])
    assert len(log) == 1
    assert log[0]["function_name"] == "do_thing"


def test_sandbox_blocks_missing_permission(tmp_path, monkeypatch):
    import plugins.registry as registry_mod
    reg = registry_mod.PluginRegistry(str(tmp_path / "plugins.db"))
    monkeypatch.setattr(registry_mod, "_instance", reg)
    from plugins.manifest import parse_manifest
    p = reg.register(parse_manifest(_manifest()))
    reg.set_status(p["id"], "enabled")
    from plugins.sandbox import PluginSandbox
    sb = PluginSandbox(str(tmp_path / "plugins.db"))
    out = sb.execute(p["id"], "danger", {}, ["vault:read"])
    assert out["allowed"] is False
    assert "vault:read" in out["blocked_reason"]


def test_example_plugin_manifest_valid():
    """The bundled example plugin manifest must parse."""
    import os
    from plugins.manifest import load_manifest_file
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "plugins", "example_tool", "plugin.json",
    )
    m = load_manifest_file(path)
    assert m.name == "example-tool"
