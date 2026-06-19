"""Phase 13 tests — Event Monitor, CPA Ops, Market Intel, Workforce Agents."""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("HELIOS_TEST", "1")


_SINGLETONS = [
    "connectors.registry", "live_intelligence.monitor", "research.missions",
    "financial_hub.store", "fusion.engine", "event_monitor.engine",
    "cpa_ops.monitor", "market_intel.brief", "market_intel.signals",
    "workforce_agents.market_agent", "workforce_agents.economic_agent",
    "workforce_agents.regulatory_agent", "workforce_agents.research_agent",
    "workforce_agents.connector_agent", "workforce_agents.event_agent",
]


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for mod in _SINGLETONS:
        if mod in sys.modules:
            sys.modules[mod]._instance = None


# ── Event Monitor ────────────────────────────────────────────────────────────

def test_event_monitor_init():
    from event_monitor.engine import get_event_monitor
    em = get_event_monitor()
    rules = em.list_rules()
    assert len(rules) >= 6


def test_create_event():
    from event_monitor.engine import get_event_monitor
    em = get_event_monitor()
    event = em.create_event(
        category="tax_regulatory", event_type="irs_guidance",
        title="IRS Notice 2024-01 detected",
        description="New IRS notice on cryptocurrency reporting",
        severity="high", source="federal_register",
    )
    assert event["id"]
    assert event["category"] == "tax_regulatory"
    assert event["severity"] == "high"


def test_list_events():
    from event_monitor.engine import get_event_monitor
    em = get_event_monitor()
    em.create_event(category="sec_filings", event_type="material_filing",
                    title="8-K Filing", severity="medium")
    events = em.list_events(category="sec_filings")
    assert any(e["category"] == "sec_filings" for e in events)


def test_acknowledge_event():
    from event_monitor.engine import get_event_monitor
    em = get_event_monitor()
    event = em.create_event(category="system", event_type="connector_offline",
                            title="FRED offline", severity="medium")
    result = em.acknowledge_event(event["id"])
    assert result["status"] == "acknowledged"


def test_resolve_event():
    from event_monitor.engine import get_event_monitor
    em = get_event_monitor()
    event = em.create_event(category="deadline", event_type="deadline_reminder",
                            title="Q4 Filing Due", severity="critical")
    result = em.resolve_event(event["id"])
    assert result["status"] == "resolved"


def test_add_deadline():
    from event_monitor.engine import get_event_monitor
    em = get_event_monitor()
    deadline = em.add_deadline(
        title="Q4 Estimated Tax", deadline_date="2024-01-15",
        category="tax", reminder_days=14,
    )
    assert deadline["id"]
    assert deadline["deadline_date"] == "2024-01-15"


def test_list_deadlines():
    from event_monitor.engine import get_event_monitor
    em = get_event_monitor()
    em.add_deadline(title="Form 1040 Due", deadline_date="2024-04-15", category="tax")
    deadlines = em.list_deadlines(category="tax")
    assert any(d["title"] == "Form 1040 Due" for d in deadlines)


def test_record_system_health():
    from event_monitor.engine import get_event_monitor
    em = get_event_monitor()
    em.record_system_health("fred_connector", "ok", "Connected successfully")
    em.record_system_health("sec_connector", "error", "Connection timeout")
    events = em.list_events(category="system")
    assert any("sec_connector" in e["title"] for e in events)


def test_event_monitor_stats():
    from event_monitor.engine import get_event_monitor
    stats = get_event_monitor().stats()
    assert "active_events" in stats
    assert "active_rules" in stats
    assert "pending_deadlines" in stats


# ── CPA Ops Monitor ──────────────────────────────────────────────────────────

def test_cpa_monitor_init():
    from cpa_ops.monitor import get_cpa_monitor
    monitor = get_cpa_monitor()
    assert monitor is not None


def test_create_advisory():
    from cpa_ops.monitor import get_cpa_monitor
    monitor = get_cpa_monitor()
    advisory = monitor.create_advisory(
        title="FASB ASU Impact Advisory",
        body="New FASB standard ASU 2024-01 affects lease accounting...",
        advisory_type="accounting_standards",
        priority="high",
    )
    assert advisory["id"]
    assert advisory["status"] == "draft"


def test_list_advisories():
    from cpa_ops.monitor import get_cpa_monitor
    monitor = get_cpa_monitor()
    monitor.create_advisory(title="Test Advisory", body="Body text", priority="normal")
    advisories = monitor.list_advisories()
    assert isinstance(advisories, list)
    assert len(advisories) >= 1


def test_add_compliance_item():
    from cpa_ops.monitor import get_cpa_monitor
    monitor = get_cpa_monitor()
    item = monitor.add_compliance_item(
        title="File Form 1099", description="Annual 1099 filing requirement",
        category="tax", due_date="2024-01-31", priority="high",
    )
    assert item["id"]
    assert item["category"] == "tax"


def test_list_compliance():
    from cpa_ops.monitor import get_cpa_monitor
    monitor = get_cpa_monitor()
    monitor.add_compliance_item(title="1065 Partnership Return", category="tax", due_date="2024-03-15")
    items = monitor.list_compliance(category="tax")
    assert any(i["title"] == "1065 Partnership Return" for i in items)


def test_cpa_stats():
    from cpa_ops.monitor import get_cpa_monitor
    stats = get_cpa_monitor().stats()
    assert "total_updates" in stats
    assert "draft_advisories" in stats
    assert "open_compliance_items" in stats


# ── Market Intelligence ──────────────────────────────────────────────────────

def test_market_briefing_init():
    from market_intel.brief import get_market_briefing
    briefing = get_market_briefing()
    assert briefing is not None


def test_generate_daily_brief():
    from market_intel.brief import get_market_briefing
    briefing = get_market_briefing()
    brief = briefing.generate_daily_brief()
    assert brief["id"]
    assert brief["headline"]
    assert brief["sentiment"] in ("bullish", "bearish", "neutral")
    assert 0 <= brief["risk_score"] <= 1


def test_get_latest_brief():
    from market_intel.brief import get_market_briefing
    briefing = get_market_briefing()
    briefing.generate_daily_brief()
    latest = briefing.get_latest_brief()
    assert latest is not None
    assert latest["headline"]


def test_list_briefs():
    from market_intel.brief import get_market_briefing
    briefing = get_market_briefing()
    briefs = briefing.list_briefs()
    assert isinstance(briefs, list)


def test_create_watchlist_alert():
    from market_intel.brief import get_market_briefing
    briefing = get_market_briefing()
    alert = briefing.create_watchlist_alert(
        symbol="AAPL", alert_type="price_move",
        title="AAPL +5.2% today", price=178.5, change_pct=5.2,
    )
    assert alert["symbol"] == "AAPL"
    assert alert["change_pct"] == 5.2


def test_snapshot_macro():
    from market_intel.brief import get_market_briefing
    briefing = get_market_briefing()
    snap = briefing.snapshot_macro(
        gdp_growth=2.8, inflation_rate=3.1, unemployment_rate=3.7,
        fed_funds_rate=5.33, yield_10y=4.2, vix=15.3, outlook="neutral",
    )
    assert snap["gdp_growth"] == 2.8
    assert snap["outlook"] == "neutral"


def test_signal_detector_init():
    from market_intel.signals import get_signal_detector
    detector = get_signal_detector()
    assert detector is not None


def test_create_signal():
    from market_intel.signals import get_signal_detector
    detector = get_signal_detector()
    signal = detector.create_signal(
        signal_type="momentum", symbol="NVDA",
        title="NVDA +8.5% momentum signal",
        description="Strong upward momentum detected",
        strength=0.85, direction="up", timeframe="short",
    )
    assert signal["id"]
    assert signal["direction"] == "up"
    assert signal["strength"] == 0.85


def test_list_signals():
    from market_intel.signals import get_signal_detector
    detector = get_signal_detector()
    detector.create_signal(signal_type="macro_shift", title="CPI Spike",
                           strength=0.7, direction="up")
    signals = detector.list_signals()
    assert isinstance(signals, list)


def test_dismiss_signal():
    from market_intel.signals import get_signal_detector
    detector = get_signal_detector()
    signal = detector.create_signal(signal_type="volume_spike", title="Volume Alert", strength=0.6)
    result = detector.dismiss_signal(signal["id"])
    assert result["status"] == "dismissed"


def test_signal_stats():
    from market_intel.signals import get_signal_detector
    stats = get_signal_detector().stats()
    assert "active_signals" in stats
    assert "by_type" in stats


# ── Workforce Agents ─────────────────────────────────────────────────────────

def test_agent_base_memory():
    from workforce_agents.base import BaseAgent, AgentResult
    import abc

    class TestAgent(BaseAgent):
        agent_id = "test_agent"
        agent_name = "Test"
        domain = "test"
        description = "For testing"

        def _execute(self, inputs: dict) -> AgentResult:
            self.remember("test_key", {"value": 42})
            recalled = self.recall("test_key")
            return AgentResult(
                agent_id=self.agent_id,
                findings=[{"recalled": recalled}],
                proposed_actions=[],
                summary="Test complete",
            )

    agent = TestAgent()
    result = agent.run()
    assert result.error is None
    assert len(result.findings) == 1
    assert result.findings[0]["recalled"]["value"] == 42


def test_agent_propose_action():
    from workforce_agents.base import BaseAgent, AgentResult, list_pending_approvals

    class ActionAgent(BaseAgent):
        agent_id = "action_test_agent"
        agent_name = "Action Test"
        domain = "test"
        description = "Test actions"

        def _execute(self, inputs: dict) -> AgentResult:
            return AgentResult(
                agent_id=self.agent_id,
                findings=[],
                proposed_actions=[{
                    "type": "advisory",
                    "title": "Test Advisory Action",
                    "description": "Requires approval",
                    "payload": {"data": "test"},
                    "requires_approval": True,
                }],
                summary="Action proposed",
            )

    agent = ActionAgent()
    agent.run()
    pending = list_pending_approvals()
    assert any(a["title"] == "Test Advisory Action" for a in pending)


def test_approve_action():
    from workforce_agents.base import BaseAgent, AgentResult, list_pending_approvals, approve_action

    class ApproveAgent(BaseAgent):
        agent_id = "approve_test_agent_unique"
        agent_name = "Approve Test"
        domain = "test"
        description = "Test approval"

        def _execute(self, inputs: dict) -> AgentResult:
            return AgentResult(
                agent_id=self.agent_id,
                findings=[],
                proposed_actions=[{
                    "type": "alert",
                    "title": "Approval Candidate",
                    "description": "",
                    "payload": {},
                    "requires_approval": True,
                }],
                summary="",
            )

    agent = ApproveAgent()
    agent.run()
    pending = list_pending_approvals()
    candidates = [a for a in pending if a["title"] == "Approval Candidate"]
    assert len(candidates) >= 1
    result = approve_action(candidates[0]["id"], approved_by="test_user")
    assert result["status"] == "approved"
    assert result["approved_by"] == "test_user"


def test_market_agent_run():
    from workforce_agents.market_agent import get_market_agent
    agent = get_market_agent()
    result = agent.run()
    assert result.agent_id == "agent_market"
    assert isinstance(result.findings, list)
    assert isinstance(result.proposed_actions, list)


def test_economic_agent_run():
    from workforce_agents.economic_agent import get_economic_agent
    agent = get_economic_agent()
    result = agent.run()
    assert result.agent_id == "agent_economic"
    assert isinstance(result.findings, list)


def test_regulatory_agent_run():
    from workforce_agents.regulatory_agent import get_regulatory_agent
    agent = get_regulatory_agent()
    result = agent.run()
    assert result.agent_id == "agent_regulatory"
    assert isinstance(result.findings, list)


def test_research_agent_run():
    from workforce_agents.research_agent import get_research_agent
    agent = get_research_agent()
    result = agent.run()
    assert result.agent_id == "agent_research"
    assert isinstance(result.findings, list)


def test_connector_agent_run():
    from workforce_agents.connector_agent import get_connector_agent
    agent = get_connector_agent()
    result = agent.run()
    assert result.agent_id == "agent_connector"
    assert isinstance(result.findings, list)


def test_event_agent_run():
    from workforce_agents.event_agent import get_event_agent
    agent = get_event_agent()
    result = agent.run()
    assert result.agent_id == "agent_event"
    assert isinstance(result.findings, list)


def test_agent_run_history():
    from workforce_agents.market_agent import get_market_agent
    agent = get_market_agent()
    agent.run()
    runs = agent.list_runs()
    assert len(runs) >= 1
    assert runs[0]["agent_id"] == "agent_market"


def test_agent_stats():
    from workforce_agents.base import agent_stats
    stats = agent_stats()
    assert "completed_runs" in stats
    assert "pending_approvals" in stats
