"""HELIOS Intelligence Sidecar — FastAPI app.

The compute tier of HELIOS: the Quant Research Engine and Accounting Intelligence
Engine, served on localhost for the Electron app to call. Bound to 127.0.0.1 and
unreachable off-box; the service layer it wraps is pure-Python and unit-tested.

Run:  uvicorn app.main:app --host 127.0.0.1 --port 8420
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config
from .routers import (
    accounting, accounting_intel, accounting_platform_router, execution_router, health, markets,
    n8n_router, personal, quant, quant_research, workbench,
    security_router, backup_router, sync_router, health_router,
    workspaces_router, licensing_router, monitoring_router, updates_router,
    plugins_router, public_api_router, webhooks_router,
    reasoning_router, intelligence_router, forecasting_router, advisory_router, executive_router,
    knowledge_router, memory_router, rag_router, synthesis_router, self_improvement_router,
    connectors_router, live_intel_router, research_router, financial_hub_router,
    cpa_ops_router, market_intel_router, fusion_router, event_monitor_router, agents_router,
    quant_lab_router, backtesting_router, portfolio_lab_router, risk_analytics_router,
    factor_router, altdata_router, thesis_router, earnings_router, macro_router,
    quant_agents_router, portfolio_command_router,
    voice_router, conversation_router, notifications_router, presence_router,
    ambient_router, llm_runtime_router, desktop_router, voice_agents_router,
    runtime_router, feature_flags_router, release_channels_router,
    migrations_router, plugin_upgrades_router, feedback_router,
    evolution_router, stability_router, ops_dashboard_router,
    discovery_router, language_academy_router,
    tradingview_router, robinhood_router, tts_router,
)
from .services.market_data import DataUnavailable

app = FastAPI(
    title="HELIOS Intelligence Sidecar",
    version=config.VERSION,
    description="Quant Research + Accounting Intelligence compute tier for HELIOS.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(app://\.|http://(localhost|127\.0\.0\.1)(:\d+)?)$",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def _value_error(_req: Request, exc: ValueError) -> JSONResponse:
    # Bad/insufficient input → 400 with the underlying message.
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(DataUnavailable)
async def _data_unavailable(_req: Request, exc: DataUnavailable) -> JSONResponse:
    # Provider/network problem → 503 so the caller can degrade gracefully.
    return JSONResponse(status_code=503, content={"error": str(exc)})


app.include_router(health.router)
app.include_router(quant.router)
app.include_router(quant_research.router)
app.include_router(markets.router)
app.include_router(accounting.router)
app.include_router(accounting_intel.router)
app.include_router(n8n_router.router)
app.include_router(personal.router)
app.include_router(accounting_platform_router.router)
app.include_router(workbench.router)
app.include_router(execution_router.router)
# Phase 9 — security, backup, sync, health
app.include_router(security_router.router)
app.include_router(backup_router.router)
app.include_router(sync_router.router)
app.include_router(health_router.router)
# Phase 10 — productization, deployment & commercial readiness
app.include_router(workspaces_router.router)
app.include_router(licensing_router.router)
app.include_router(monitoring_router.router)
app.include_router(updates_router.router)
app.include_router(plugins_router.router)
app.include_router(public_api_router.router)
app.include_router(webhooks_router.router)
# Phase 11 — autonomous intelligence & strategic reasoning
app.include_router(reasoning_router.router)
app.include_router(intelligence_router.router)
app.include_router(forecasting_router.router)
app.include_router(advisory_router.router)
app.include_router(executive_router.router)
# Phase 12 — knowledge engine, RAG, institutional memory & self-improving intelligence
app.include_router(knowledge_router.router)
app.include_router(memory_router.router)
app.include_router(rag_router.router)
app.include_router(synthesis_router.router)
app.include_router(self_improvement_router.router)
# Phase 13 — live connectors, research automation, financial hub, CPA ops, market intel, agents
app.include_router(connectors_router.router)
app.include_router(live_intel_router.router)
app.include_router(research_router.router)
app.include_router(financial_hub_router.router)
app.include_router(cpa_ops_router.router)
app.include_router(market_intel_router.router)
app.include_router(fusion_router.router)
app.include_router(event_monitor_router.router)
app.include_router(agents_router.router)
# Phase 14 — quant lab, backtesting, portfolio, risk, factors, alt-data,
# thesis, earnings, macro, investment agents & portfolio command center
app.include_router(quant_lab_router.router)
app.include_router(backtesting_router.router)
app.include_router(portfolio_lab_router.router)
app.include_router(risk_analytics_router.router)
app.include_router(factor_router.router)
app.include_router(altdata_router.router)
app.include_router(thesis_router.router)
app.include_router(earnings_router.router)
app.include_router(macro_router.router)
app.include_router(quant_agents_router.router)
app.include_router(portfolio_command_router.router)
# Phase 15 — voice OS, conversation, notifications, presence, ambient, LLM runtime, desktop, agents
app.include_router(voice_router.router)
app.include_router(conversation_router.router)
app.include_router(notifications_router.router)
app.include_router(presence_router.router)
app.include_router(ambient_router.router)
app.include_router(llm_runtime_router.router)
app.include_router(desktop_router.router)
app.include_router(voice_agents_router.router)
# Phase 15.5 — live operations, stability & continuous evolution
app.include_router(runtime_router.router)
app.include_router(feature_flags_router.router)
app.include_router(release_channels_router.router)
app.include_router(migrations_router.router)
app.include_router(plugin_upgrades_router.router)
app.include_router(feedback_router.router)
app.include_router(evolution_router.router)
app.include_router(stability_router.router)
app.include_router(ops_dashboard_router.router)
# Phase 15.75 — investment discovery engine & language academy
app.include_router(discovery_router.router)
app.include_router(language_academy_router.router)
# Phase 16 — TradingView live data, Robinhood agentic trading, ElevenLabs TTS
app.include_router(tradingview_router.router)
app.include_router(robinhood_router.router)
app.include_router(tts_router.router)


def main() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":  # pragma: no cover
    main()
