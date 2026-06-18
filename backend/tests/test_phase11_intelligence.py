"""Phase 11 — Cross-domain graph, opportunity, and risk engine tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "intel.db")


# ---- Graph ----

def test_graph_add_and_query(db):
    from intelligence.graph import IntelligenceGraph
    g = IntelligenceGraph(db)
    a = g.add_node("accounting", "Ledger")
    b = g.add_node("portfolio", "Cash")
    g.add_edge(a["id"], b["id"], "drives", 0.8)
    assert len(g.nodes()) == 2
    assert len(g.edges()) == 1
    assert len(g.neighbors(a["id"])) == 1


def test_graph_build_from_domains(db):
    from intelligence.graph import IntelligenceGraph
    g = IntelligenceGraph(db)
    result = g.build_from_domains()
    assert result["nodes"] >= 4
    assert result["edges"] >= 3


def test_graph_discover_relationships(db):
    from intelligence.graph import IntelligenceGraph
    g = IntelligenceGraph(db)
    insights = g.discover_relationships()
    assert isinstance(insights, list)


# ---- Opportunities ----

def test_opportunity_scan_and_list(db):
    from intelligence.opportunities import OpportunityEngine
    oe = OpportunityEngine(db)
    found = oe.scan()
    assert isinstance(found, list)
    # With no accounting data, defaults still allow some detectors to fire or none;
    # listing must round-trip whatever was persisted.
    listed = oe.list(status="open")
    assert len(listed) == len(found)


def test_opportunity_scoring_bounds(db):
    from intelligence.opportunities import OpportunityEngine, _score
    assert 0 <= _score(1.0, 0.0, 1.0) <= 100
    assert _score(1.0, 0.0, 1.0) > _score(0.1, 5.0, 0.2)


def test_opportunity_status_update(db):
    from intelligence.opportunities import OpportunityEngine
    oe = OpportunityEngine(db)
    o = oe._persist("tax", "Test opp", "desc", 0.8, 0.2, 0.7, {})
    assert oe.set_status(o["id"], "actioned") is True
    assert oe.get(o["id"])["status"] == "actioned"


# ---- Risks ----

def test_risk_scan_and_severity(db):
    from intelligence.risks import RiskEngine, _severity
    assert _severity(80) == "critical"
    assert _severity(50) == "high"
    assert _severity(25) == "medium"
    assert _severity(5) == "low"
    re = RiskEngine(db)
    found = re.scan()
    assert isinstance(found, list)


def test_risk_persist_and_summary(db):
    from intelligence.risks import RiskEngine
    re = RiskEngine(db)
    re._persist("accounting", "Cash risk", "desc", 0.8, 0.9, ["mitigate"])
    summary = re.summary()
    assert summary["open_risks"] >= 1
    assert summary["max_score"] > 0


def test_risk_filter_by_severity(db):
    from intelligence.risks import RiskEngine
    re = RiskEngine(db)
    re._persist("accounting", "Critical", "d", 0.9, 0.95, [])
    crit = re.list(severity="critical")
    assert all(r["severity"] == "critical" for r in crit)
