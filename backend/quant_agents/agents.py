"""
Phase 14 investment agents — Portfolio Manager, Quant Research, Risk Officer,
Macro Strategist, Earnings Analyst, Factor Research.

Each reuses the Phase 13 BaseAgent (dedicated memory, performance tracking,
approval queue). Agents propose research, watchlists, trade ideas, rebalance
proposals, and risk warnings — all advisory, all routed to the approval queue.
Nothing executes automatically; no broker orders, no account modification.
"""
from __future__ import annotations
from workforce_agents.base import BaseAgent, AgentResult


class PortfolioManagerAgent(BaseAgent):
    agent_id = "agent_portfolio_manager"
    agent_name = "Portfolio Manager Agent"
    domain = "markets"
    description = "Reviews portfolios, proposes rebalances and risk-aware allocation (advisory)"
    allowed_action_types = ["rebalance_proposal", "advisory", "alert"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings, actions = [], []
        try:
            from portfolio.engine import get_portfolio_engine
            pe = get_portfolio_engine()
            portfolios = pe.list()
            for pf in portfolios[:10]:
                findings.append({"type": "portfolio", "id": pf["id"], "name": pf["name"],
                                 "method": pf["method"], "sharpe": pf.get("stats", {}).get("sharpe")})
                prop = pe.propose_rebalance(pf["id"])
                if prop.get("turnover", 0) > 0.05:
                    actions.append({
                        "type": "rebalance_proposal",
                        "title": f"Rebalance {pf['name']} (turnover {prop['turnover']:.1%})",
                        "description": f"{len(prop['trades'])} trades, est. cost {prop['est_cost']:.2%}",
                        "payload": {"proposal_id": prop["id"], "portfolio_id": pf["id"]},
                        "requires_approval": True,
                    })
        except Exception as e:
            findings.append({"type": "error", "source": "portfolio", "error": str(e)})
        self.remember("last_portfolio_count", len(findings))
        return AgentResult(self.agent_id, findings, actions,
                           f"Portfolio Manager reviewed {len(findings)} portfolio(s), proposed {len(actions)} rebalance(s).")


class QuantResearchAgent(BaseAgent):
    agent_id = "agent_quant_research"
    agent_name = "Quant Research Agent"
    domain = "markets"
    description = "Runs experiments, evaluates strategies, surfaces research findings"
    allowed_action_types = ["advisory", "signal"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings, actions = [], []
        try:
            from quant_lab.lab import get_quant_lab
            lab = get_quant_lab()
            strategies = lab.list_strategies()
            for s in strategies[:10]:
                findings.append({"type": "strategy", "id": s["id"], "name": s["name"],
                                 "status": s["status"], "version": s["version"]})
            experiments = lab.list_experiments(limit=10)
            for e in experiments[:5]:
                sharpe = e.get("result", {}).get("metrics", {}).get("sharpe")
                findings.append({"type": "experiment", "name": e["name"], "sharpe": sharpe})
                if sharpe is not None and sharpe > 1.0:
                    actions.append({
                        "type": "advisory",
                        "title": f"Promising strategy: {e['name']} (Sharpe {sharpe:.2f})",
                        "description": "Out-of-sample validation recommended before deployment.",
                        "payload": {"experiment": e["name"]},
                        "requires_approval": False,
                    })
        except Exception as e:
            findings.append({"type": "error", "source": "quant_lab", "error": str(e)})
        return AgentResult(self.agent_id, findings, actions,
                           f"Quant Research processed {len(findings)} item(s).")


class RiskOfficerAgent(BaseAgent):
    agent_id = "agent_risk_officer"
    agent_name = "Risk Officer Agent"
    domain = "markets"
    description = "Monitors portfolio risk, runs stress tests, raises risk warnings"
    allowed_action_types = ["alert", "advisory"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings, actions = [], []
        try:
            from portfolio.engine import get_portfolio_engine
            from risk_analytics.engine import get_risk_engine
            pe = get_portfolio_engine()
            re = get_risk_engine()
            for pf in pe.list()[:10]:
                holdings = [{"symbol": s, "weight": w} for s, w in pf.get("weights", {}).items()]
                report = re.analyze(holdings, name=pf["name"], portfolio_id=pf["id"], persist=False)
                health = report.get("health_score")
                findings.append({"type": "risk", "portfolio": pf["name"], "health_score": health})
                if health is not None and health < 50:
                    actions.append({
                        "type": "alert",
                        "title": f"Risk warning: {pf['name']} health {health}/100",
                        "description": f"VaR {report.get('var', {}).get('historical_pct')}%, "
                                       f"concentration {report.get('concentration', {}).get('herfindahl')}",
                        "payload": {"portfolio_id": pf["id"], "health_score": health},
                        "requires_approval": False,
                    })
        except Exception as e:
            findings.append({"type": "error", "source": "risk", "error": str(e)})
        return AgentResult(self.agent_id, findings, actions,
                           f"Risk Officer assessed {len(findings)} portfolio(s), raised {len(actions)} warning(s).")


class MacroStrategistAgent(BaseAgent):
    agent_id = "agent_macro_strategist"
    agent_name = "Macro Strategist Agent"
    domain = "finance"
    description = "Classifies macro regime, scores risk-on/off, generates economic outlook"
    allowed_action_types = ["advisory", "signal"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings, actions = [], []
        try:
            from macro.engine import get_macro_engine
            me = get_macro_engine()
            regime = me.classify_regime()
            findings.append({"type": "regime", "regime": regime["regime"],
                             "stance": regime["stance"], "risk_score": regime["risk_score"]})
            curve = regime.get("yield_curve", {})
            if curve.get("signal") == "recession_warning":
                actions.append({
                    "type": "advisory",
                    "title": "Yield curve inverted — recession signal",
                    "description": regime["outlook"],
                    "payload": {"regime": regime["regime"], "stance": regime["stance"]},
                    "requires_approval": False,
                })
            findings.append({"type": "outlook", "text": regime["outlook"]})
        except Exception as e:
            findings.append({"type": "error", "source": "macro", "error": str(e)})
        return AgentResult(self.agent_id, findings, actions,
                           f"Macro Strategist classified regime with {len(findings)} finding(s).")


class EarningsAnalystAgent(BaseAgent):
    agent_id = "agent_earnings_analyst"
    agent_name = "Earnings Analyst Agent"
    domain = "markets"
    description = "Analyzes earnings events, generates scorecards, tracks revisions"
    allowed_action_types = ["advisory", "signal"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings, actions = [], []
        try:
            from earnings.engine import get_earnings_engine
            ee = get_earnings_engine()
            for ev in ee.list_events(status="reported", limit=10):
                card = ee.scorecard(ev["id"])
                findings.append({"type": "scorecard", "symbol": ev["symbol"],
                                 "grade": card.get("grade"), "score": card.get("score")})
                if card.get("grade") in ("A", "F"):
                    actions.append({
                        "type": "advisory",
                        "title": f"Earnings scorecard {card['grade']}: {ev['symbol']}",
                        "description": f"Score {card['score']}/100 for {ev.get('period', '')}",
                        "payload": {"symbol": ev["symbol"], "grade": card["grade"]},
                        "requires_approval": False,
                    })
        except Exception as e:
            findings.append({"type": "error", "source": "earnings", "error": str(e)})
        return AgentResult(self.agent_id, findings, actions,
                           f"Earnings Analyst produced {len(findings)} scorecard finding(s).")


class FactorResearchAgent(BaseAgent):
    agent_id = "agent_factor_research"
    agent_name = "Factor Research Agent"
    domain = "markets"
    description = "Ranks factor exposures, tracks factor persistence and decay"
    allowed_action_types = ["advisory", "signal"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings, actions = [], []
        try:
            from quant_lab.factors import get_factor_library
            from financial_hub.store import get_financial_hub
            lib = get_factor_library()
            watchlist = [w["symbol"] for w in get_financial_hub().get_watchlist()]
            if watchlist:
                lib.snapshot(watchlist)
                for factor in ("value", "quality", "momentum"):
                    ranked = lib.rank(watchlist, factor)
                    if ranked:
                        top = ranked[0]
                        findings.append({"type": "factor_rank", "factor": factor,
                                         "top_symbol": top["symbol"], "score": top["score"]})
            else:
                findings.append({"type": "info", "message": "no watchlist symbols to rank"})
        except Exception as e:
            findings.append({"type": "error", "source": "factors", "error": str(e)})
        return AgentResult(self.agent_id, findings, actions,
                           f"Factor Research generated {len(findings)} ranking(s).")


_REGISTRY = {
    "portfolio_manager": PortfolioManagerAgent,
    "quant_research": QuantResearchAgent,
    "risk_officer": RiskOfficerAgent,
    "macro_strategist": MacroStrategistAgent,
    "earnings_analyst": EarningsAnalystAgent,
    "factor_research": FactorResearchAgent,
}

_instances: dict = {}


def get_quant_agent(agent_key: str):
    cls = _REGISTRY.get(agent_key)
    if not cls:
        raise ValueError(f"Unknown quant agent: {agent_key}")
    if agent_key not in _instances:
        _instances[agent_key] = cls()
    return _instances[agent_key]


def list_quant_agents() -> list[dict]:
    return [{"id": k, "agent_id": cls.agent_id, "name": cls.agent_name,
             "description": cls.description} for k, cls in _REGISTRY.items()]
