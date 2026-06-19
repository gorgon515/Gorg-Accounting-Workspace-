"""Phase 11 — Strategic reasoning, proposal loop, and learning engine tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "intel.db")


# ---- Reasoning engine ----

def test_decompose_goal():
    from reasoning.engine import StrategicReasoningEngine
    eng = StrategicReasoningEngine()
    plan = eng.decompose_goal("Pass CPA", target_value=100, horizon_months=4)
    assert len(plan["milestones"]) == 4
    assert plan["milestones"][-1]["target_cumulative"] == 100
    assert plan["milestones"][1]["depends_on"] == 1


def test_prioritize_ranking():
    from reasoning.engine import StrategicReasoningEngine
    eng = StrategicReasoningEngine()
    ranked = eng.prioritize([
        {"id": "a", "title": "low", "impact": 0.2, "effort": 0.9, "urgency": 0.1},
        {"id": "b", "title": "high", "impact": 0.9, "effort": 0.1, "urgency": 0.9},
    ])
    assert ranked[0]["id"] == "b"
    assert ranked[0]["priority_score"] > ranked[1]["priority_score"]


def test_tradeoff_analysis():
    from reasoning.engine import StrategicReasoningEngine
    eng = StrategicReasoningEngine()
    result = eng.analyze_tradeoffs([
        {"name": "safe", "benefit": 0.5, "cost": 0.2, "risk": 0.1},
        {"name": "risky", "benefit": 0.9, "cost": 0.3, "risk": 0.9},
    ])
    assert result["recommended"] in ("safe", "risky")
    assert "alternatives" in result


def test_constraint_check():
    from reasoning.engine import StrategicReasoningEngine
    eng = StrategicReasoningEngine()
    result = eng.check_constraints(
        {"demands": {"hours": 50, "budget": 1000}},
        {"hours": 40, "budget": 2000},
    )
    assert result["feasible"] is False
    assert result["violations"][0]["resource"] == "hours"


def test_recommend_runs(db, monkeypatch):
    import intelligence.opportunities as opp_mod
    import intelligence.risks as risk_mod
    monkeypatch.setattr(opp_mod, "_instance", opp_mod.OpportunityEngine(db))
    monkeypatch.setattr(risk_mod, "_instance", risk_mod.RiskEngine(db))
    from reasoning.engine import StrategicReasoningEngine
    result = StrategicReasoningEngine().recommend()
    assert "recommendations" in result
    assert "summary" in result


# ---- Proposal loop ----

def test_proposal_loop_run(db):
    from reasoning.proposals import AutonomousProposalLoop
    loop = AutonomousProposalLoop(db)
    result = loop.run_daily()
    assert "briefing" in result
    assert "proposals" in result
    assert result["proposals_created"] == len(result["proposals"])


def test_proposal_decide(db):
    from reasoning.proposals import AutonomousProposalLoop
    loop = AutonomousProposalLoop(db)
    p = loop._add("task", "Test", "detail", "rationale", 1, "test")
    assert loop.decide(p["id"], "approved")["status"] == "approved"
    pending = loop.list_proposals(status="pending")
    assert all(x["id"] != p["id"] for x in pending)


def test_proposal_decide_invalid(db):
    from reasoning.proposals import AutonomousProposalLoop
    loop = AutonomousProposalLoop(db)
    p = loop._add("task", "T", "d", "r", 1, "t")
    with pytest.raises(ValueError):
        loop.decide(p["id"], "maybe")


# ---- Learning engine ----

def test_learning_accuracy(db):
    from reasoning.learning import LearningEngine
    le = LearningEngine(db)
    rec = le.record_outcome("forecast", predicted=100, actual=90)
    assert 0 <= rec["accuracy"] <= 1
    acc = le.accuracy_by_kind("forecast")
    assert acc["samples"] == 1


def test_learning_trend(db):
    from reasoning.learning import LearningEngine
    le = LearningEngine(db)
    for i in range(20):
        le.record_outcome("forecast", predicted=100, actual=100 - (i % 5))
    trend = le.trend("forecast", window=5)
    assert trend["trend"] in ("improving", "declining", "stable")
