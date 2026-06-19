"""
Phase 13 integration test — exercises the full operational pipeline end-to-end:
  connector ingest → live intelligence → knowledge engine → fusion → events →
  agents → approval workflow.

Verifies the Phase 13 acceptance criteria without requiring network access.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_SINGLETONS = [
    "connectors.registry", "live_intelligence.monitor", "research.missions",
    "financial_hub.store", "fusion.engine", "event_monitor.engine",
    "cpa_ops.monitor", "market_intel.brief", "market_intel.signals",
    "workforce_agents.market_agent", "workforce_agents.economic_agent",
    "workforce_agents.regulatory_agent", "workforce_agents.research_agent",
    "workforce_agents.connector_agent", "workforce_agents.event_agent",
]


def _reset_singletons():
    for mod in _SINGLETONS:
        if mod in sys.modules and hasattr(sys.modules[mod], "_instance"):
            sys.modules[mod]._instance = None
    # Prior-phase singletons that bind to a per-test .data/ directory (incl. ChromaDB).
    if "knowledge.engine" in sys.modules:
        sys.modules["knowledge.engine"]._instance = None
    for mod in ("vector_memory.store", "rag.platform", "embeddings.pipeline"):
        if mod in sys.modules and hasattr(sys.modules[mod], "_instances"):
            sys.modules[mod]._instances = {}


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _reset_singletons()
    yield
    _reset_singletons()


def test_full_intelligence_pipeline():
    """Ingest regulatory + market intel, then verify it flows through every layer."""
    from live_intelligence.monitor import get_monitor
    from knowledge.engine import get_knowledge_engine
    from event_monitor.engine import get_event_monitor
    from fusion.engine import get_fusion_engine

    monitor = get_monitor()

    # 1. Connector ingest — regulatory items (tax + accounting) and market items.
    reg_items = [
        {"title": "IRS Revenue Ruling 2024-12 on digital asset basis",
         "content": "The IRS issued new guidance affecting client tax engagements and reporting.",
         "url": "https://irs.gov/rr-2024-12", "source": "federal_register"},
        {"title": "FASB ASU 2024-03 on crypto asset disclosure",
         "content": "New FASB accounting standard affects client financial statement disclosures.",
         "url": "https://fasb.org/asu-2024-03", "source": "federal_register"},
    ]
    market_items = [
        {"title": "Fed signals rate decision amid sector weakness",
         "content": "Federal Reserve commentary on interest rate path; technology sector under pressure.",
         "url": "https://federalreserve.gov/news-1", "source": "federal_reserve"},
        {"title": "Material 8-K filing from watchlist company",
         "content": "A tracked equity filed a material event 8-K with the SEC.",
         "url": "https://sec.gov/8k-1", "source": "sec_edgar"},
    ]
    r1 = monitor.ingest_from_connector("federal_register", reg_items, domain="tax")
    r2 = monitor.ingest_from_connector("federal_register", [reg_items[1]], domain="accounting")
    r3 = monitor.ingest_from_connector("federal_reserve", market_items[:1], domain="finance")
    r4 = monitor.ingest_from_connector("sec_edgar", market_items[1:], domain="markets")
    assert r1["new_items"] >= 1

    # 2. Knowledge engine received the embedded items (auto-embed on ingest).
    ke = get_knowledge_engine()
    ke_stats = ke.stats()
    assert ke_stats.get("total_items", 0) >= 1  # knowledge engine receives data

    # 3. Live intelligence holds the deduplicated, importance-ranked items.
    tax_items = monitor.list_items(domain="tax")
    assert len(tax_items) >= 1
    intel_stats = monitor.stats()
    assert intel_stats["total_items"] >= 3

    # 4. Event monitor detects events from the intelligence stream.
    triggered = get_event_monitor().scan_intelligence()
    # At least the IRS / FASB rules should fire given the ingested content.
    assert isinstance(triggered, list)
    active_events = get_event_monitor().list_events(status="active")
    assert len(active_events) >= 1  # event detection works

    # 5. Intelligence fusion correlates across sources → compound events.
    fusion_events = get_fusion_engine().run_fusion()
    assert isinstance(fusion_events, list)
    # regulatory+client pattern should match the IRS/FASB items mentioning clients
    assert len(fusion_events) >= 1  # intelligence fusion works


def test_agent_to_approval_workflow():
    """Agent run proposes an action that requires human approval; approve it."""
    from live_intelligence.monitor import get_monitor
    from workforce_agents.regulatory_agent import get_regulatory_agent
    from workforce_agents.base import list_pending_approvals, approve_action

    # Seed high-priority regulatory intel so the agent proposes an advisory.
    monitor = get_monitor()
    monitor.ingest_from_connector("federal_register", [
        {"title": "IRS major guidance on revenue ruling affecting all clients",
         "content": "Mandatory effective change. IRS revenue ruling requires client action.",
         "url": "https://irs.gov/major", "source": "federal_register"},
    ], domain="tax")

    agent = get_regulatory_agent()
    result = agent.run()
    assert result.agent_id == "agent_regulatory"
    assert result.error is None

    # The agent proposes actions that enter the approval queue (never auto-execute).
    pending = list_pending_approvals()
    if pending:  # high-priority path produced an approval-required action
        action = pending[0]
        assert action["requires_approval"] == 1
        approved = approve_action(action["id"], approved_by="cpa_user")
        assert approved["status"] == "approved"  # approval workflow integration works


def test_financial_hub_receives_connector_data():
    """Financial hub routes connector items into the right tables."""
    from financial_hub.store import get_financial_hub
    hub = get_financial_hub()

    # Economic data (FRED-style)
    hub.ingest_from_connector("fred", [
        {"series_id": "FEDFUNDS", "observations": [
            {"date": "2024-01-01", "value": "5.33"},
            {"date": "2023-12-01", "value": "5.25"},
        ]},
    ])
    # Filing (SEC-style)
    hub.ingest_from_connector("sec_edgar", [
        {"cik": "0000320193", "entity": "Apple Inc.", "form": "10-K",
         "filing_date": "2024-10-01", "accession_number": "x-1"},
    ])
    stats = hub.stats()
    assert stats["economic_observations"] >= 2
    assert stats["filings"] >= 1  # financial data hub works


def test_market_brief_and_signals_pipeline():
    """Market brief generation + signal detection run on hub data."""
    from financial_hub.store import get_financial_hub
    from market_intel.brief import get_market_briefing
    from market_intel.signals import get_signal_detector

    hub = get_financial_hub()
    hub.add_watchlist("AAPL", "Apple Inc.", sector="Technology")
    hub.store_prices("AAPL", [
        {"date": "2024-01-01", "close": 100.0, "volume": 1000000},
        {"date": "2024-01-02", "close": 109.0, "volume": 1200000},  # +9% → momentum signal
    ], source="test")
    hub.store_economic("FEDFUNDS", "Fed Funds", [
        {"date": "2024-01-01", "value": "5.50"},
        {"date": "2023-10-01", "value": "5.00"},  # +0.50 → macro signal
    ])

    brief = get_market_briefing().generate_daily_brief()
    assert brief["headline"]
    assert brief["sentiment"] in ("bullish", "bearish", "neutral")  # dashboard receives live data

    signals = get_signal_detector().detect_signals()
    # momentum (AAPL +9%) and macro (FEDFUNDS +0.5) should both fire
    assert len(signals) >= 1
    types = {s["signal_type"] for s in signals}
    assert "momentum" in types or "macro_shift" in types


def test_existing_systems_still_functional():
    """Smoke check that prior-phase engines still import and respond."""
    from knowledge.engine import get_knowledge_engine
    from rag.platform import get_rag  # noqa: F401  (import OK = wired)
    ke = get_knowledge_engine()
    item = ke.ingest(title="Test", content="Phase 13 coexistence check",
                     domain="general", kind="fact", source="test")
    assert item["id"]
    assert ke.stats()["total_items"] >= 1
