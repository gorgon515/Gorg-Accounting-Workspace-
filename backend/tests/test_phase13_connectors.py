"""Phase 13 tests — Universal Connector Framework."""
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("HELIOS_TEST", "1")


_SINGLETONS = [
    "connectors.registry", "connectors.providers.fred", "connectors.providers.sec_edgar",
    "connectors.providers.federal_register", "connectors.providers.bls",
    "connectors.providers.yahoo_finance",
]


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for mod in _SINGLETONS:
        if mod in sys.modules:
            sys.modules[mod]._instance = None


# ── Connector base & registry ────────────────────────────────────────────────

def test_connector_meta():
    from connectors.base import ConnectorMeta
    meta = ConnectorMeta(
        id="test_conn", name="Test", kind="api", category="test",
        auth_type="none",
    )
    assert meta.id == "test_conn"
    assert meta.requires_credential is False


def test_fetch_result():
    from connectors.base import FetchResult
    r = FetchResult(connector_id="x", status="ok", items=[{"a": 1}])
    assert r.status == "ok"
    assert len(r.items) == 1


def test_registry_init():
    from connectors.registry import get_registry
    registry = get_registry()
    connectors = registry.list()
    assert isinstance(connectors, list)
    assert len(connectors) >= 5  # built-in connectors seeded


def test_registry_get():
    from connectors.registry import get_registry
    registry = get_registry()
    conn = registry.get("fred")
    assert conn is not None
    assert conn["id"] == "fred"


def test_registry_set_status():
    from connectors.registry import get_registry
    registry = get_registry()
    result = registry.set_status("fred", "disabled")
    assert result["status"] == "disabled"
    result2 = registry.set_status("fred", "active")
    assert result2["status"] == "active"


def test_registry_update_config():
    from connectors.registry import get_registry
    registry = get_registry()
    result = registry.update_config("fred", {"api_key": "test123"})
    assert result is not None


def test_registry_store_credential():
    from connectors.registry import get_registry
    registry = get_registry()
    registry.store_credential("fred", "vault://fred_key", "fred_***")


def test_registry_stats():
    from connectors.registry import get_registry
    stats = get_registry().stats()
    assert "total" in stats
    assert stats["total"] >= 5


def test_registry_list_filter():
    from connectors.registry import get_registry
    registry = get_registry()
    market = registry.list(category="market")
    finance = registry.list(category="finance")
    assert isinstance(market, list)
    assert isinstance(finance, list)


def test_registry_health_check():
    from connectors.registry import get_registry
    registry = get_registry()
    result = registry.health_check("fred")
    assert "healthy" in result
    assert "connector_id" in result


# ── Built-in providers ───────────────────────────────────────────────────────

def test_fred_connector_meta():
    from connectors.providers.fred import FREDConnector
    assert FREDConnector.meta.id == "fred"
    assert FREDConnector.meta.kind in ("api", "economic_data")


def test_sec_edgar_connector_meta():
    from connectors.providers.sec_edgar import SECEdgarConnector
    assert SECEdgarConnector.meta.id == "sec_edgar"


def test_federal_register_connector_meta():
    from connectors.providers.federal_register import FederalRegisterConnector
    assert FederalRegisterConnector.meta.id == "federal_register"


def test_bls_connector_meta():
    from connectors.providers.bls import BLSConnector
    assert BLSConnector.meta.id == "bls"


def test_yahoo_finance_connector_meta():
    from connectors.providers.yahoo_finance import YahooFinanceConnector
    assert YahooFinanceConnector.meta.id == "yahoo_finance"


def test_workspace_connectors_registered():
    from connectors.registry import _CONNECTORS
    assert "google_workspace" in _CONNECTORS
    assert "slack" in _CONNECTORS
    assert "notion" in _CONNECTORS


def test_workspace_connector_requires_credential():
    from connectors.providers.workspace_connectors import _make_workspace_connector
    Cls = _make_workspace_connector("test_ws_isolated", "Test WS", "workspace", "Test desc")
    instance = Cls()
    result = instance.fetch()
    assert result.status in ("offline", "error")


def test_registry_fetch_offline_connector():
    from connectors.registry import get_registry
    registry = get_registry()
    result = registry.fetch("google_workspace")
    # FetchResult dataclass
    assert result.status in ("offline", "error", "ok")


def test_poll_log():
    from connectors.registry import get_registry
    registry = get_registry()
    registry.poll_log("fred", status="ok", items_fetched=5, duration_ms=120)
    logs = registry.poll_logs("fred", limit=5)
    assert isinstance(logs, list)
