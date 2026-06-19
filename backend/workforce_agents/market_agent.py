"""
Market Intelligence Agent: monitors equity markets, price moves, earnings, and watchlist events.
Proposes alerts for human review — never executes trades autonomously.
"""
from __future__ import annotations
from .base import BaseAgent, AgentResult


class MarketIntelligenceAgent(BaseAgent):
    agent_id = "agent_market"
    agent_name = "Market Intelligence Agent"
    domain = "markets"
    description = "Monitors equity prices, watchlist alerts, earnings events, and SEC filings"
    allowed_action_types = ["signal", "alert"]

    def _execute(self, inputs: dict) -> AgentResult:
        findings = []
        proposed_actions = []

        try:
            from market_intel.brief import get_market_briefing
            briefing = get_market_briefing()
            brief = briefing.generate_daily_brief()
            findings.append({
                "type": "market_brief",
                "title": brief.get("headline", ""),
                "sentiment": brief.get("sentiment", "neutral"),
                "risk_score": brief.get("risk_score", 0.5),
                "key_events": brief.get("key_events", [])[:5],
            })
        except Exception as e:
            findings.append({"type": "error", "source": "market_brief", "error": str(e)})

        try:
            from market_intel.signals import get_signal_detector
            detector = get_signal_detector()
            signals = detector.detect_signals()
            for sig in signals[:5]:
                findings.append({
                    "type": "signal",
                    "signal_type": sig.get("signal_type"),
                    "title": sig.get("title"),
                    "direction": sig.get("direction"),
                    "strength": sig.get("strength"),
                })
                if sig.get("strength", 0) >= 0.7:
                    proposed_actions.append({
                        "type": "alert",
                        "title": f"Market Signal: {sig.get('title', '')}",
                        "description": sig.get("description", ""),
                        "payload": {"signal_id": sig.get("id"), "strength": sig.get("strength")},
                        "requires_approval": False,
                    })
        except Exception as e:
            findings.append({"type": "error", "source": "signal_detector", "error": str(e)})

        try:
            from financial_hub.store import get_financial_hub
            hub = get_financial_hub()
            filings = hub.list_filings(form="8-K", limit=5)
            for filing in filings:
                findings.append({
                    "type": "filing",
                    "entity": filing.get("entity"),
                    "form": filing.get("form"),
                    "date": filing.get("filing_date"),
                })
        except Exception as e:
            findings.append({"type": "error", "source": "filings", "error": str(e)})

        self.remember("last_run_findings_count", len(findings))
        summary = f"Market Intelligence Agent processed {len(findings)} findings, proposed {len(proposed_actions)} action(s)."
        return AgentResult(
            agent_id=self.agent_id,
            findings=findings,
            proposed_actions=proposed_actions,
            summary=summary,
        )


_instance = None


def get_market_agent() -> MarketIntelligenceAgent:
    global _instance
    if _instance is None:
        _instance = MarketIntelligenceAgent()
    return _instance
