"""Phase 15 backend unit tests — Voice OS, Conversation, Notifications, Presence,
Ambient, LLM Runtime, Desktop, Voice Agents."""
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


# ── Voice OS ──────────────────────────────────────────────────────────────────

class TestVoiceOS:
    def test_create_profile(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        p = v.create_profile("Test Profile", stt_engine="whisper", tts_engine="system")
        assert p["name"] == "Test Profile"
        assert p["stt_engine"] == "whisper"
        assert p["wake_word"] == "helios"

    def test_list_profiles(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        v.create_profile("Alpha")
        v.create_profile("Beta")
        profiles = v.list_profiles()
        assert len(profiles) == 2

    def test_set_mode(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        result = v.set_mode("always_listening")
        assert result["mode"] == "always_listening"
        state = v.get_mode()
        assert state["mode"] == "always_listening"

    def test_invalid_mode_raises(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        with pytest.raises(ValueError):
            v.set_mode("invalid_mode")

    def test_set_stt_engine(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        r = v.set_stt_engine("vosk")
        assert r["stt_engine"] == "vosk"

    def test_session_lifecycle(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        session = v.start_session()
        sid = session["id"]
        t1 = v.add_turn(sid, "user", "Hello HELIOS")
        t2 = v.add_turn(sid, "assistant", "Good morning.")
        assert t1["role"] == "user"
        assert t2["role"] == "assistant"
        full = v.get_session(sid)
        assert len(full["turns"]) == 2
        ended = v.end_session(sid, summary="Test session ended")
        assert ended["ended_at"] is not None

    def test_wake_event(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        e = v.record_wake_event("helios", 0.99)
        assert e["keyword"] == "helios"
        history = v.wake_history()
        assert len(history) == 1

    def test_synthesize(self):
        from voice_os.engine import get_voice_os
        r = get_voice_os().synthesize("Hello world")
        assert r["status"] == "synthesized"
        assert r["estimated_duration_sec"] > 0

    def test_transcribe(self):
        from voice_os.engine import get_voice_os
        r = get_voice_os().transcribe(text_input="Test transcription")
        assert r["text"] == "Test transcription"
        assert r["confidence"] > 0

    def test_capabilities(self):
        from voice_os.engine import get_voice_os
        c = get_voice_os().capabilities()
        assert "whisper" in c["stt_engines"]
        assert "piper" in c["tts_engines"]
        assert "always_listening" in c["modes"]

    def test_activate_profile(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        p = v.create_profile("Active Profile")
        v.set_active_profile(p["id"])
        profiles = v.list_profiles()
        active = [x for x in profiles if x["is_active"]]
        assert len(active) == 1
        assert active[0]["name"] == "Active Profile"

    def test_stats(self):
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        v.create_profile("P1")
        s = v.start_session()
        v.add_turn(s["id"], "user", "hi")
        v.record_wake_event()
        stats = v.stats()
        assert stats["profiles"] == 1
        assert stats["sessions"] == 1
        assert stats["turns"] == 1
        assert stats["wake_events"] == 1


# ── Conversation ──────────────────────────────────────────────────────────────

class TestConversation:
    def test_create_thread(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        t = c.create_thread("Test Thread", mode="chat")
        assert t["title"] == "Test Thread"
        assert t["mode"] == "chat"
        assert t["status"] in ("active", "open")

    def test_send_message(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        t = c.create_thread("Thread")
        msg = c.send_message(t["id"], "user", "Hello")
        assert msg["role"] == "user"
        assert msg["content"] == "Hello"

    def test_get_thread_with_messages(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        t = c.create_thread("Thread")
        c.send_message(t["id"], "user", "Msg 1")
        c.send_message(t["id"], "assistant", "Msg 2")
        full = c.get_thread(t["id"])
        assert len(full["messages"]) == 2

    def test_get_context(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        t = c.create_thread("T")
        for i in range(15):
            c.send_message(t["id"], "user", f"Message {i}")
        ctx = c.get_context(t["id"], max_turns=5)
        assert len(ctx) <= 5

    def test_close_thread(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        t = c.create_thread("T")
        closed = c.close_thread(t["id"], summary="Done")
        assert closed["status"] == "closed"

    def test_summarize_thread(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        t = c.create_thread("T")
        c.send_message(t["id"], "user", "What is the portfolio return?")
        c.send_message(t["id"], "assistant", "The return is 12%.")
        summary = c.summarize_thread(t["id"])
        assert "key_points" in summary
        assert summary["turn_count"] == 2

    def test_analytics(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        c.create_thread("T1")
        c.create_thread("T2")
        a = c.analytics()
        assert a["total_threads"] == 2
        assert a["active_threads"] == 2

    def test_search_threads(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        c.create_thread("Portfolio analysis")
        c.create_thread("Tax research")
        results = c.search_threads("portfolio")
        assert any("Portfolio" in r["title"] for r in results)

    def test_stats(self):
        from conversation.engine import get_conversation_engine
        c = get_conversation_engine()
        t = c.create_thread("T")
        c.send_message(t["id"], "user", "hi")
        s = c.stats()
        assert s["total_threads"] == 1
        assert s["total_messages"] == 1


# ── Notifications ─────────────────────────────────────────────────────────────

class TestNotifications:
    def test_send(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        r = n.send("Test Alert", body="Something happened", priority="high", category="system")
        assert r["title"] == "Test Alert"
        assert r["priority"] == "high"

    def test_list(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        n.send("N1", priority="low")
        n.send("N2", priority="high")
        items = n.list()
        assert len(items) == 2

    def test_mark_read(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        r = n.send("N1")
        ok = n.mark_read(r["id"])
        assert ok
        items = n.list(status="read")
        assert any(i["id"] == r["id"] for i in items)

    def test_mark_all_read(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        n.send("N1")
        n.send("N2")
        n.send("N3")
        marked = n.mark_all_read()
        assert marked == 3
        stats = n.stats()
        assert stats["unread"] == 0

    def test_quiet_hours(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        result = n.set_quiet_hours(start_hour=22, end_hour=7, enabled=True)
        assert result["enabled"]
        qh = n.get_quiet_hours()
        assert qh["start_hour"] == 22

    def test_focus_mode(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        r = n.set_focus_mode(enabled=True, duration_minutes=60)
        assert r["enabled"]
        fm = n.get_focus_mode()
        assert fm["enabled"]

    def test_escalate(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        r = n.send("N1", priority="low")
        escalated = n.escalate(r["id"], "urgent")
        assert escalated["priority"] == "urgent"

    def test_priority_scoring(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        r_critical = n.send("Critical!", priority="critical")
        r_low = n.send("Info", priority="low")
        assert r_critical["score"] > r_low["score"]

    def test_channels(self):
        from notifications.engine import get_notification_engine
        channels = get_notification_engine().channels()
        assert len(channels) > 0

    def test_batch_pending(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        n.send("Market alert 1", category="market")
        n.send("Market alert 2", category="market")
        n.send("System alert", category="system")
        batched = n.batch_pending()
        assert len(batched) > 0

    def test_dismiss(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        r = n.send("N1")
        ok = n.dismiss(r["id"])
        assert ok
        items = n.list(status="dismissed")
        assert any(i["id"] == r["id"] for i in items)

    def test_stats(self):
        from notifications.engine import get_notification_engine
        n = get_notification_engine()
        n.send("N1", priority="high")
        n.send("N2", priority="low")
        s = n.stats()
        assert s["total"] == 2
        assert s["unread"] == 2


# ── Presence ──────────────────────────────────────────────────────────────────

class TestPresence:
    def test_set_mode(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        r = p.set_mode("market")
        assert r["mode"] == "market"

    def test_get_state(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        p.set_mode("study")
        state = p.get_state()
        assert state["mode"] == "study"

    def test_update_context(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        r = p.update_context(app="VS Code", task="Writing tests")
        assert r["app"] == "VS Code"
        assert r["task"] == "Writing tests"

    def test_calendar_status(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        p.set_calendar_status("in_meeting", meeting_title="Daily Standup", ends_at=time.time() + 3600)
        cal = p.get_calendar_status()
        assert cal["status"] == "in_meeting"
        assert cal["meeting_title"] == "Daily Standup"

    def test_focus_mode(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        r = p.set_focus(enabled=True, duration_min=90, goal="Finish portfolio analysis")
        assert r["enabled"]
        assert r["goal"] == "Finish portfolio analysis"
        focus = p.get_focus()
        assert focus["enabled"]

    def test_mode_history(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        p.set_mode("work")
        p.set_mode("market")
        p.set_mode("break")
        history = p.mode_history()
        assert len(history) >= 2

    def test_adaptive_config_market(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        p.set_mode("market")
        cfg = p.adaptive_config()
        assert cfg["notification_level"] == "high"
        assert cfg["briefing_freq"] == "hourly"

    def test_adaptive_config_study(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        p.set_mode("study")
        cfg = p.adaptive_config()
        assert cfg["notification_level"] == "low"

    def test_stats(self):
        from presence.engine import get_presence_engine
        p = get_presence_engine()
        p.set_mode("accounting")
        s = p.stats()
        assert "current_mode" in s
        assert s["current_mode"] == "accounting"


# ── Ambient ───────────────────────────────────────────────────────────────────

class TestAmbient:
    def test_generate_briefing(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        b = a.generate_briefing(include_sections=["system_health", "market"])
        assert "sections" in b
        assert "voice_text" in b
        assert b["word_count"] > 0
        assert "Good morning" in b["voice_text"]

    def test_get_latest_briefing(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        a.generate_briefing(include_sections=["market"])
        latest = a.get_latest_briefing()
        assert latest is not None
        assert "sections" in latest

    def test_briefing_history(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        a.generate_briefing(include_sections=["market"])
        a.generate_briefing(include_sections=["system_health"])
        history = a.briefing_history()
        assert len(history) == 2

    def test_add_reminder(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        r = a.add_reminder("CPA Study", body="Review chapter 5",
                           remind_at=time.time() + 3600, category="study")
        assert r["title"] == "CPA Study"
        assert r["category"] == "study"

    def test_list_reminders(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        a.add_reminder("R1", remind_at=time.time() + 3600)
        a.add_reminder("R2", remind_at=time.time() + 7200)
        reminders = a.list_reminders()
        assert len(reminders) == 2

    def test_dismiss_reminder(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        r = a.add_reminder("R1", remind_at=time.time() + 3600)
        ok = a.dismiss_reminder(r["id"])
        assert ok
        active = a.list_reminders(active_only=True)
        assert not any(x["id"] == r["id"] for x in active)

    def test_check_triggers(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        past_time = time.time() - 10
        a.add_reminder("Past Reminder", remind_at=past_time)
        a.add_reminder("Future Reminder", remind_at=time.time() + 9999)
        triggered = a.check_triggers()
        assert len(triggered) == 1
        assert triggered[0]["title"] == "Past Reminder"

    def test_record_alert(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        alert = a.record_alert("market", "Market Alert", body="SPX dropped 2%",
                               source="market_monitor", severity="high")
        assert alert["alert_type"] == "market"
        assert alert["severity"] == "high"

    def test_list_alerts(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        a.record_alert("system", "System Alert", severity="info")
        a.record_alert("market", "Market Alert", severity="high")
        alerts = a.list_alerts()
        assert len(alerts) == 2

    def test_stats(self):
        from ambient.engine import get_ambient_engine
        a = get_ambient_engine()
        a.generate_briefing(include_sections=["market"])
        a.add_reminder("R1", remind_at=time.time() + 3600)
        a.record_alert("system", "Alert 1")
        s = a.stats()
        assert s["briefings_generated"] == 1
        assert s["active_reminders"] == 1
        assert s["unacknowledged_alerts"] == 1


# ── LLM Runtime ───────────────────────────────────────────────────────────────

class TestLLMRuntime:
    def test_list_models(self):
        from llm_runtime.engine import get_llm_runtime
        models = get_llm_runtime().list_models()
        assert len(models) == 6

    def test_local_models(self):
        from llm_runtime.engine import get_llm_runtime
        local = get_llm_runtime().list_models(local_only=True)
        assert len(local) == 2
        assert all(m["local"] for m in local)

    def test_capability_filter(self):
        from llm_runtime.engine import get_llm_runtime
        reasoning_models = get_llm_runtime().list_models(capability="reasoning")
        assert len(reasoning_models) >= 2
        assert all("reasoning" in m["capabilities"] for m in reasoning_models)

    def test_get_model(self):
        from llm_runtime.engine import get_llm_runtime
        m = get_llm_runtime().get_model("gpt-4o")
        assert m is not None
        assert m["provider"] == "openai"
        assert m["context_window"] == 128000

    def test_route_task_chat(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime().route_task("chat")
        assert "model" in r
        assert "reason" in r

    def test_route_task_local(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime().route_task("chat", requires_local=True)
        m = get_llm_runtime().get_model(r["model"])
        assert m["local"]

    def test_budget_context(self):
        from llm_runtime.engine import get_llm_runtime
        messages = [{"role": "user", "content": f"Message {i}" * 100} for i in range(20)]
        budgeted = get_llm_runtime().budget_context(messages, max_tokens=500)
        assert len(budgeted) < len(messages)

    def test_optimize_prompt(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        optimized = r.optimize_prompt("  hello world  ", "chat")
        assert optimized == "hello world"
        code_opt = r.optimize_prompt("write a sort function", "code")
        assert code_opt.startswith("You are an expert programmer")

    def test_cache_response(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        r.cache_response("hash123", "Cached response", "gpt-4o", 50)
        cached = r.get_cached("hash123")
        assert cached is not None
        assert cached["response"] == "Cached response"

    def test_cache_ttl_expired(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        r.cache_response("old_hash", "Old response", "gpt-4o", 10)
        result = r.get_cached("old_hash", ttl_sec=0)
        assert result is None

    def test_record_inference(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        log = r.record_inference("gpt-4o", 100, 200, 850.5, "chat")
        assert log["model"] == "gpt-4o"
        assert log["latency_ms"] == 850.5

    def test_inference_metrics(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        r.record_inference("gpt-4o-mini", 50, 100, 400.0, "summarization")
        r.record_inference("gpt-4o-mini", 60, 120, 500.0, "summarization")
        metrics = r.inference_metrics("gpt-4o-mini")
        assert metrics["total_calls"] == 2
        assert metrics["avg_latency_ms"] == 450.0

    def test_detect_gpu(self):
        from llm_runtime.engine import get_llm_runtime
        gpu = get_llm_runtime().detect_gpu()
        assert "available" in gpu
        assert "devices" in gpu
        assert isinstance(gpu["vram_gb"], float)

    def test_register_model(self):
        from llm_runtime.engine import get_llm_runtime
        r = get_llm_runtime()
        m = r.register_model("custom-model", "custom", context_window=16000,
                             capabilities=["chat","analysis"])
        assert m["name"] == "custom-model"
        assert "analysis" in m["capabilities"]
        all_models = r.list_models()
        assert len(all_models) == 7

    def test_stats(self):
        from llm_runtime.engine import get_llm_runtime
        s = get_llm_runtime().stats()
        assert s["total_models"] == 6
        assert s["local_models"] == 2


# ── Desktop ───────────────────────────────────────────────────────────────────

class TestDesktop:
    def test_get_system_info(self):
        from desktop.engine import get_desktop_engine
        info = get_desktop_engine().get_system_info()
        assert "platform" in info
        assert "cpu_percent" in info

    def test_list_directory_home(self):
        from desktop.engine import get_desktop_engine
        result = get_desktop_engine().list_directory("")
        assert "entries" in result
        assert "path" in result

    def test_launch_app_requires_approval(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        r = d.launch_app("Firefox", require_approval=True)
        assert r["status"] == "pending_approval"
        pending = d.list_approvals()
        assert len(pending) == 1
        assert pending[0]["action_type"] == "launch_app"

    def test_clipboard_write_approval(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        r = d.clipboard_write("secret content", require_approval=True)
        assert r["status"] == "pending_approval"

    def test_open_file_approval(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        r = d.open_file("/home/user/doc.pdf", require_approval=True)
        assert r["status"] == "pending_approval"

    def test_approve_action(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        d.launch_app("App", require_approval=True)
        pending = d.list_approvals()
        aid = pending[0]["id"]
        result = d.approve(aid, note="Approved by user")
        assert result["status"] == "approved"

    def test_reject_action(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        d.launch_app("App", require_approval=True)
        pending = d.list_approvals()
        aid = pending[0]["id"]
        result = d.reject(aid, note="Rejected")
        assert result["status"] == "rejected"

    def test_create_automation(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        a = d.create_automation(
            "Daily Backup",
            trigger="scheduled",
            steps=[{"action": "backup_files"}, {"action": "compress"}],
        )
        assert a["name"] == "Daily Backup"
        assert len(a["steps"]) == 2

    def test_run_automation_requires_approval(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        a = d.create_automation("Test Auto", "manual", [{"action": "do_thing"}])
        r = d.run_automation(a["id"], require_approval=True)
        assert r["status"] == "pending_approval"

    def test_focus_window_simulated(self):
        from desktop.engine import get_desktop_engine
        r = get_desktop_engine().focus_window("HELIOS")
        assert r["status"] == "simulated"

    def test_stats(self):
        from desktop.engine import get_desktop_engine
        d = get_desktop_engine()
        d.launch_app("App", require_approval=True)
        d.create_automation("Auto", "manual", [])
        s = d.stats()
        assert s["pending_approvals"] == 1
        assert s["automations"] == 1
