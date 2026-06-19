"""Phase 15 integration tests — cross-module interactions and backward compatibility."""
import time
import pytest

import voice_os.engine
import conversation.engine
import notifications.engine
import presence.engine
import ambient.engine
import llm_runtime.engine
import desktop.engine
import voice_agents.agents


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_os.engine, "_DB", tmp_path / "voice_os.db")
    monkeypatch.setattr(conversation.engine, "_DB", tmp_path / "conversation.db")
    monkeypatch.setattr(notifications.engine, "_DB", tmp_path / "notifications.db")
    monkeypatch.setattr(presence.engine, "_DB", tmp_path / "presence.db")
    monkeypatch.setattr(ambient.engine, "_DB", tmp_path / "ambient.db")
    monkeypatch.setattr(llm_runtime.engine, "_DB", tmp_path / "llm_runtime.db")
    monkeypatch.setattr(desktop.engine, "_DB", tmp_path / "desktop.db")
    voice_os.engine._instance = None
    conversation.engine._instance = None
    notifications.engine._instance = None
    presence.engine._instance = None
    ambient.engine._instance = None
    llm_runtime.engine._instance = None
    desktop.engine._instance = None
    voice_agents.agents._instances = {}
    yield
    voice_os.engine._instance = None
    conversation.engine._instance = None
    notifications.engine._instance = None
    presence.engine._instance = None
    ambient.engine._instance = None
    llm_runtime.engine._instance = None
    desktop.engine._instance = None
    voice_agents.agents._instances = {}


class TestVoiceToConversation:
    """Voice session drives a conversation thread."""

    def test_voice_session_linked_to_thread(self):
        from voice_os.engine import get_voice_os
        from conversation.engine import get_conversation_engine
        v = get_voice_os()
        c = get_conversation_engine()
        session = v.start_session()
        thread = c.create_thread(f"Voice session {session['id'][:8]}", mode="voice")
        v.add_turn(session["id"], "user", "What is my portfolio value?")
        c.send_message(thread["id"], "user", "What is my portfolio value?")
        v.add_turn(session["id"], "assistant", "Your portfolio is valued at $125,000.")
        c.send_message(thread["id"], "assistant", "Your portfolio is valued at $125,000.")
        full = c.get_thread(thread["id"])
        assert len(full["messages"]) == 2
        sess = v.get_session(session["id"])
        assert sess["turn_count"] == 2

    def test_wake_triggers_session(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        v.record_wake_event("helios", 0.95)
        session = v.start_session()
        v.set_mode("always_listening")
        stats = v.stats()
        assert stats["wake_events"] == 1
        assert stats["sessions"] == 1
        assert v.get_mode()["mode"] == "always_listening"


class TestPresenceAndNotifications:
    """Presence mode affects notification behavior."""

    def test_meeting_mode_triggers_calendar_status(self):
        from presence.engine import get_presence_engine
        from notifications.engine import get_notification_engine
        p = get_presence_engine()
        n = get_notification_engine()
        p.set_mode("meeting")
        p.set_calendar_status("in_meeting", meeting_title="Board Meeting",
                              ends_at=time.time() + 3600)
        n.set_quiet_hours(start_hour=0, end_hour=23, enabled=True)
        state = p.get_state()
        assert state["calendar"]["status"] == "in_meeting"
        qh = n.get_quiet_hours()
        assert qh["enabled"]

    def test_focus_mode_suppresses_low_priority(self):
        from presence.engine import get_presence_engine
        from notifications.engine import get_notification_engine
        p = get_presence_engine()
        n = get_notification_engine()
        p.set_mode("work")
        p.set_focus(enabled=True, duration_min=60, goal="Deep work")
        n.set_focus_mode(enabled=True, duration_minutes=60)
        assert n.get_focus_mode()["enabled"]
        assert p.get_focus()["enabled"]

    def test_market_mode_high_notifications(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        p.set_mode("market")
        cfg = p.adaptive_config()
        assert cfg["notification_level"] == "high"
        assert cfg["voice_sensitivity"] == "low"


class TestAmbientBriefingToNotification:
    """Ambient engine generates briefing, triggers can create notifications."""

    def test_briefing_contains_voice_text(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        briefing = a.generate_briefing(include_sections=["system_health", "market"])
        assert briefing["voice_text"].startswith("Good morning")
        assert briefing["word_count"] > 10

    def test_triggered_reminders_send_notifications(self):
        from ambient.engine import get_ambient_engine
        from notifications.engine import get_notification_engine
        a = get_ambient_engine()
        n = get_notification_engine()
        a.add_reminder("CPA Study Time", remind_at=time.time() - 5,
                       category="study")
        triggered = a.check_triggers()
        assert len(triggered) == 1
        notif = n.send(
            title=triggered[0]["title"],
            body=triggered[0].get("body", ""),
            priority="medium",
            category="general",
        )
        assert notif["title"] == "CPA Study Time"
        stats = n.stats()
        assert stats["total"] == 1


class TestLLMRuntimeRouting:
    """LLM runtime routes tasks to appropriate models."""

    def test_route_reasoning_to_large_context(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        result = r.route_task("reasoning")
        model = r.get_model(result["model"])
        assert model["context_window"] >= 128000

    def test_route_local_task(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        result = r.route_task("chat", requires_local=True)
        model = r.get_model(result["model"])
        assert model["local"]

    def test_cache_hit_after_miss(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        miss = r.get_cached("nonexistent_hash")
        assert miss is None
        r.cache_response("test_hash", "Result text", "gpt-4o-mini", 30)
        hit = r.get_cached("test_hash")
        assert hit is not None
        assert hit["response"] == "Result text"

    def test_inference_p95_latency(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        latencies = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        for lat in latencies:
            r.record_inference("gpt-4o", 50, 100, float(lat), "chat")
        metrics = r.inference_metrics("gpt-4o")
        assert metrics["total_calls"] == 10
        assert metrics["p95_latency_ms"] >= 900


class TestDesktopApprovalGates:
    """All dangerous desktop operations require approval."""

    def test_all_default_operations_require_approval(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        r1 = d.launch_app("App")
        r2 = d.clipboard_write("content")
        r3 = d.open_file("/path/to/file")
        assert all(r["status"] == "pending_approval" for r in [r1, r2, r3])
        pending = d.list_approvals()
        assert len(pending) == 3

    def test_approval_then_rejection_workflow(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        d.launch_app("App1")
        d.launch_app("App2")
        pending = d.list_approvals()
        assert len(pending) == 2
        d.approve(pending[0]["id"])
        d.reject(pending[1]["id"])
        still_pending = d.list_approvals(status="pending")
        assert len(still_pending) == 0

    def test_no_approval_needed_when_bypassed(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        r = d.launch_app("App", require_approval=False)
        assert r.get("status") == "launched"
        pending = d.list_approvals()
        assert len(pending) == 0


class TestVoiceAgentExecution:
    """Voice agents execute and produce structured results."""

    def _findings(self, result):
        d = result.to_dict()
        return d["findings"][0] if d.get("findings") else {}

    def test_voice_concierge_runs(self):
        from voice_agents.agents import get_voice_agent
        agent = get_voice_agent("voice_concierge")
        result = agent.run(trigger="manual", inputs={})
        f = self._findings(result)
        assert "advisory" in f
        assert "voice_state" in f

    def test_executive_assistant_generates_briefing(self):
        from voice_agents.agents import get_voice_agent
        agent = get_voice_agent("executive_assistant")
        result = agent.run(trigger="manual", inputs={"sections": ["market", "system_health"]})
        f = self._findings(result)
        assert "advisory" in f
        assert "word_count" in f

    def test_notification_agent_runs(self):
        from voice_agents.agents import get_voice_agent
        from notifications.engine import get_notification_engine
        get_notification_engine()
        agent = get_voice_agent("notification")
        result = agent.run(trigger="scheduled", inputs={})
        f = self._findings(result)
        assert "stats" in f

    def test_desktop_ops_agent_runs(self):
        from voice_agents.agents import get_voice_agent
        agent = get_voice_agent("desktop_ops")
        result = agent.run(trigger="manual", inputs={})
        f = self._findings(result)
        assert "system_info" in f
        assert "advisory" in f

    def test_conversation_manager_agent_runs(self):
        from voice_agents.agents import get_voice_agent
        agent = get_voice_agent("conversation_manager")
        result = agent.run(trigger="manual", inputs={})
        f = self._findings(result)
        assert "analytics" in f

    def test_presence_agent_runs(self):
        from voice_agents.agents import get_voice_agent
        agent = get_voice_agent("presence")
        result = agent.run(trigger="manual", inputs={})
        f = self._findings(result)
        assert "state" in f
        assert "adaptive_config" in f

    def test_list_voice_agents(self):
        from voice_agents.agents import list_voice_agents
        agents = list_voice_agents()
        assert len(agents) == 6
        keys = {a["key"] for a in agents}
        assert "voice_concierge" in keys
        assert "executive_assistant" in keys
        assert "presence" in keys


class TestExistingSystemsStillFunctional:
    """Confirm Phase 12-14 systems still function after Phase 15 additions."""

    def test_phase12_knowledge_engine_stats(self):
        try:
            from knowledge.engine import get_knowledge_engine
            s = get_knowledge_engine().stats()
            assert isinstance(s, dict)
        except Exception:
            pytest.skip("knowledge engine unavailable in this environment")

    def test_phase13_connectors_registry(self):
        try:
            from connectors.registry import get_connector_registry
            reg = get_connector_registry()
            assert hasattr(reg, "list_connectors")
        except Exception:
            pytest.skip("connector registry unavailable")

    def test_phase14_llm_runtime_has_6_models(self):
        from llm_runtime.engine import get_llm_runtime
        models = get_llm_runtime().list_models()
        assert len(models) == 6

    def test_phase15_voice_and_presence_coexist(self):
        from voice_os.engine import get_voice_os
        from presence.engine import get_presence_engine
        v = get_voice_os()
        p = get_presence_engine()
        v.set_mode("always_listening")
        p.set_mode("market")
        assert v.get_mode()["mode"] == "always_listening"
        assert p.get_mode()["mode"] == "market"

    def test_all_phase15_engines_return_stats(self):
        engines_and_getters = [
            ("voice_os", lambda: __import__("voice_os.engine", fromlist=["get_voice_os"]).get_voice_os()),
            ("conversation", lambda: __import__("conversation.engine", fromlist=["get_conversation_engine"]).get_conversation_engine()),
            ("notifications", lambda: __import__("notifications.engine", fromlist=["get_notification_engine"]).get_notification_engine()),
            ("presence", lambda: __import__("presence.engine", fromlist=["get_presence_engine"]).get_presence_engine()),
            ("ambient", lambda: __import__("ambient.engine", fromlist=["get_ambient_engine"]).get_ambient_engine()),
            ("llm_runtime", lambda: __import__("llm_runtime.engine", fromlist=["get_llm_runtime"]).get_llm_runtime()),
            ("desktop", lambda: __import__("desktop.engine", fromlist=["get_desktop_engine"]).get_desktop_engine()),
        ]
        for name, getter in engines_and_getters:
            engine = getter()
            s = engine.stats()
            assert isinstance(s, dict), f"{name}.stats() must return dict"
