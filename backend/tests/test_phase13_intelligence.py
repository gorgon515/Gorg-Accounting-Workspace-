"""Phase 13 tests — Live Intelligence, Research, Financial Hub, Fusion."""
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("HELIOS_TEST", "1")


_SINGLETONS = [
    "connectors.registry", "live_intelligence.monitor", "research.missions",
    "financial_hub.store", "fusion.engine",
]


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for mod in _SINGLETONS:
        if mod in sys.modules:
            sys.modules[mod]._instance = None


# ── Live Intelligence Monitor ────────────────────────────────────────────────

def test_monitor_init():
    from live_intelligence.monitor import get_monitor
    monitor = get_monitor()
    assert monitor is not None


def test_ingest_items():
    from live_intelligence.monitor import get_monitor
    monitor = get_monitor()
    items = [
        {"title": "IRS Notice 2024-01", "content": "New tax guidance issued by IRS",
         "url": "https://irs.gov/notice-2024-01", "source": "federal_register"},
        {"title": "FASB ASU 2024-01", "content": "Accounting standard update from FASB",
         "url": "https://fasb.org/asu-2024-01", "source": "federal_register"},
    ]
    result = monitor.ingest_from_connector("federal_register", items, domain="tax")
    assert result["new_items"] >= 0


def test_ingest_deduplication():
    from live_intelligence.monitor import get_monitor
    monitor = get_monitor()
    item = {"title": "Dedup Test", "content": "Content", "url": "https://test.com/1", "source": "test"}
    r1 = monitor.ingest_from_connector("test_conn", [item], domain="tax")
    r2 = monitor.ingest_from_connector("test_conn", [item], domain="tax")
    assert r2["new_items"] == 0  # duplicate not re-ingested


def test_list_items():
    from live_intelligence.monitor import get_monitor
    monitor = get_monitor()
    monitor.ingest_from_connector("sec_edgar", [
        {"title": "10-K Filing", "content": "Annual report filing", "url": "https://sec.gov/1", "source": "sec_edgar"},
    ], domain="markets")
    items = monitor.list_items(domain="markets")
    assert isinstance(items, list)


def test_create_alert():
    from live_intelligence.monitor import get_monitor
    monitor = get_monitor()
    alert = monitor.create_alert(
        title="Test Alert", description="Test alert description",
        severity="high", domain="markets",
    )
    assert alert["id"]
    assert alert["status"] == "new"


def test_acknowledge_alert():
    from live_intelligence.monitor import get_monitor
    monitor = get_monitor()
    alert = monitor.create_alert(title="Ack Test", description="", severity="medium")
    result = monitor.acknowledge_alert(alert["id"])
    assert result["status"] == "acknowledged"


def test_create_signal():
    from live_intelligence.monitor import get_monitor
    monitor = get_monitor()
    signal = monitor.create_signal(
        title="Test Signal", description="Signal desc",
        domain="markets", signal_type="macro", strength=0.75,
    )
    assert signal["id"]
    assert signal["confidence"] == 0.75


def test_add_monitor_config():
    from live_intelligence.monitor import get_monitor
    monitor = get_monitor()
    result = monitor.add_monitor(
        name="Tax Watch", domain="tax",
        keywords=["irs", "revenue ruling"],
        connectors=["federal_register"],
    )
    assert result["id"]
    monitors = monitor.list_monitors()
    assert any(m["name"] == "Tax Watch" for m in monitors)


def test_monitor_stats():
    from live_intelligence.monitor import get_monitor
    stats = get_monitor().stats()
    assert "total_items" in stats
    assert "active_alerts" in stats


# ── Research Missions ────────────────────────────────────────────────────────

def test_research_missions_init():
    from research.missions import get_research_missions
    rm = get_research_missions()
    assert rm is not None


def test_teams_seeded():
    from research.missions import get_research_missions
    teams = get_research_missions().teams()
    assert len(teams) >= 6
    team_ids = {t["id"] for t in teams}
    assert "market" in team_ids
    assert "accounting" in team_ids
    assert "tax" in team_ids


def test_create_mission():
    from research.missions import get_research_missions
    rm = get_research_missions()
    mission = rm.create_mission(
        name="Test Tax Research", description="Monitor tax changes",
        team="tax", topics=["irs", "revenue ruling"], schedule="daily",
    )
    assert mission["id"]
    assert mission["name"] == "Test Tax Research"
    assert mission["team"] == "tax"


def test_get_mission():
    from research.missions import get_research_missions
    rm = get_research_missions()
    m = rm.create_mission(name="Get Test", team="market")
    fetched = rm.get_mission(m["id"])
    assert fetched["id"] == m["id"]


def test_list_missions():
    from research.missions import get_research_missions
    rm = get_research_missions()
    rm.create_mission(name="Listed Mission", team="economic")
    missions = rm.list_missions()
    assert any(m["name"] == "Listed Mission" for m in missions)


def test_pause_mission():
    from research.missions import get_research_missions
    rm = get_research_missions()
    m = rm.create_mission(name="Pause Test", team="market")
    paused = rm.pause_mission(m["id"])
    assert paused["status"] == "paused"


def test_research_stats():
    from research.missions import get_research_missions
    stats = get_research_missions().stats()
    assert "active_missions" in stats
    assert "teams" in stats


# ── Financial Data Hub ───────────────────────────────────────────────────────

def test_financial_hub_init():
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    assert hub is not None


def test_store_prices():
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    bars = [
        {"date": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000000},
        {"date": "2024-01-02", "open": 103, "high": 107, "low": 102, "close": 106, "volume": 900000},
    ]
    stored = hub.store_prices("AAPL", bars, source="test")
    assert stored == 2


def test_get_prices():
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    hub.store_prices("MSFT", [{"date": "2024-01-01", "close": 300, "volume": 500000}])
    prices = hub.get_prices("MSFT")
    assert len(prices) >= 1
    assert prices[0]["symbol"] == "MSFT"


def test_store_economic():
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    observations = [
        {"date": "2024-01-01", "value": "5.33"},
        {"date": "2023-10-01", "value": "5.25"},
    ]
    stored = hub.store_economic("FEDFUNDS", "Federal Funds Rate", observations, source="fred")
    assert stored == 2


def test_get_economic():
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    hub.store_economic("UNRATE", "Unemployment", [{"date": "2024-01-01", "value": "3.7"}])
    data = hub.get_economic("UNRATE")
    assert len(data) >= 1


def test_store_filing():
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    hub.store_filing({
        "cik": "0000320193", "entity": "Apple Inc.", "form": "10-K",
        "filing_date": "2024-10-01", "accession_number": "0000320193-24-000001",
        "primary_doc": "aapl-20240928.htm",
    })
    filings = hub.list_filings(form="10-K")
    assert any(f["entity"] == "Apple Inc." for f in filings)


def test_watchlist_operations():
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()
    hub.add_watchlist("GOOG", "Alphabet Inc.", sector="Technology")
    wl = hub.get_watchlist()
    assert any(w["symbol"] == "GOOG" for w in wl)
    hub.remove_watchlist("GOOG")
    wl2 = hub.get_watchlist()
    assert not any(w["symbol"] == "GOOG" for w in wl2)


def test_financial_hub_stats():
    from financial_hub.store import get_financial_hub
    stats = get_financial_hub().stats()
    assert "price_bars" in stats
    assert "watchlist_size" in stats


# ── Fusion Engine ────────────────────────────────────────────────────────────

def test_fusion_engine_init():
    from fusion.engine import get_fusion_engine
    fe = get_fusion_engine()
    rules = fe.list_rules()
    assert len(rules) >= 5


def test_fusion_create_event():
    from fusion.engine import get_fusion_engine
    fe = get_fusion_engine()
    event = fe.create_event(
        title="Test Fusion Event",
        description="Test description",
        pattern="regulatory+client",
        severity="high",
        confidence=0.8,
        domains=["tax"],
        action_type="advisory_opportunity",
    )
    assert event["id"]
    assert event["confidence"] == 0.8


def test_fusion_list_events():
    from fusion.engine import get_fusion_engine
    fe = get_fusion_engine()
    fe.create_event(title="List Test", description="", pattern="market+portfolio", severity="medium")
    events = fe.list_events(status="new")
    assert isinstance(events, list)


def test_fusion_acknowledge_event():
    from fusion.engine import get_fusion_engine
    fe = get_fusion_engine()
    event = fe.create_event(title="Ack Test", description="", pattern="macro+sector")
    result = fe.acknowledge_event(event["id"])
    assert result["status"] == "acknowledged"


def test_fusion_pattern_matching():
    from fusion.engine import get_fusion_engine
    fe = get_fusion_engine()
    items = [
        {"id": "1", "title": "IRS Revenue Ruling", "content": "New tax regulation from IRS"},
        {"id": "2", "title": "Client Advisory", "content": "Client engagement update"},
        {"id": "3", "title": "Market Update", "content": "stock market performance"},
    ]
    matched = fe._match_pattern(["regulatory"], items)
    assert len(matched) >= 1
    assert any(i["id"] == "1" for i in matched)


def test_fusion_stats():
    from fusion.engine import get_fusion_engine
    stats = get_fusion_engine().stats()
    assert "active_rules" in stats
    assert "total_events" in stats
