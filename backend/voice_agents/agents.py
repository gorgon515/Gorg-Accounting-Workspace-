from workforce_agents.base import BaseAgent, AgentResult

_instances: dict = {}


class VoiceConciergeAgent(BaseAgent):
    agent_id = "agent_voice_concierge"

    def _execute(self, inputs: dict) -> AgentResult:
        from voice_os.engine import get_voice_os
        v = get_voice_os()
        state = v.get_mode()
        stats = v.stats()
        sessions = v.list_sessions(limit=5)
        advisory = (
            f"Voice OS in {state['mode']} mode. "
            f"STT: {state['stt_engine']}, TTS: {state['tts_engine']}. "
            f"{stats['sessions']} total sessions, {stats['turns']} turns recorded."
        )
        return AgentResult(
            agent_id=self.agent_id,
            findings=[{
                "voice_state": state,
                "stats": stats,
                "recent_sessions": len(sessions),
                "advisory": advisory,
            }],
            proposed_actions=[],
        )


class ExecutiveAssistantAgent(BaseAgent):
    agent_id = "agent_executive_assistant"

    def _execute(self, inputs: dict) -> AgentResult:
        from ambient.engine import get_ambient_engine
        engine = get_ambient_engine()
        sections = inputs.get("sections") if isinstance(inputs, dict) else None
        briefing = engine.generate_briefing(include_sections=sections)
        wc = briefing.get("word_count", 0)
        section_names = list(briefing.get("sections", {}).keys())
        return AgentResult(
            agent_id=self.agent_id,
            findings=[{
                "briefing_id": briefing.get("id"),
                "sections": section_names,
                "word_count": wc,
                "voice_text_preview": briefing.get("voice_text", "")[:200],
                "advisory": (
                    f"Morning briefing generated with {len(section_names)} sections "
                    f"and {wc} words. Ready for voice playback."
                ),
            }],
            proposed_actions=[],
        )


class NotificationAgent(BaseAgent):
    agent_id = "agent_notification"

    def _execute(self, inputs: dict) -> AgentResult:
        from notifications.engine import get_notification_engine
        ne = get_notification_engine()
        stats = ne.stats()
        unread = stats.get("unread", 0)
        proposed = []
        if unread > 10:
            proposed.append({
                "type": "notification_batch_review",
                "title": f"{unread} unread notifications",
                "description": f"{unread} unread notifications have accumulated. Batch review recommended.",
                "payload": {"unread": unread, "stats": stats},
                "requires_approval": False,
            })
        triggered = []
        try:
            from ambient.engine import get_ambient_engine
            triggered = get_ambient_engine().check_triggers()
            for t in triggered:
                ne.send(
                    title=t["title"],
                    body=t.get("body", ""),
                    priority="medium",
                    category=t.get("category", "general"),
                    channel="desktop",
                    source="ambient_trigger",
                )
        except Exception:
            pass
        return AgentResult(
            agent_id=self.agent_id,
            findings=[{
                "stats": stats,
                "triggered_reminders": len(triggered),
                "advisory": f"{unread} unread notifications. {len(triggered)} reminder(s) triggered.",
            }],
            proposed_actions=proposed,
        )


class DesktopOperationsAgent(BaseAgent):
    agent_id = "agent_desktop_ops"

    def _execute(self, inputs: dict) -> AgentResult:
        from desktop.engine import get_desktop_engine
        de = get_desktop_engine()
        sys_info = de.get_system_info()
        pending = de.list_approvals()
        stats = de.stats()
        cpu = sys_info.get("cpu_percent", 0)
        mem = sys_info.get("memory_percent", 0)
        proposed = []
        if cpu > 85:
            proposed.append({
                "type": "high_cpu_alert",
                "title": f"CPU usage critical: {cpu:.0f}%",
                "description": f"CPU usage is {cpu:.0f}%. Investigate running processes.",
                "payload": {"cpu_percent": cpu},
                "requires_approval": False,
            })
        return AgentResult(
            agent_id=self.agent_id,
            findings=[{
                "system_info": sys_info,
                "pending_approvals": len(pending),
                "stats": stats,
                "advisory": (
                    f"System: CPU {cpu:.0f}%, RAM {mem:.0f}%. "
                    f"{len(pending)} desktop action(s) pending approval."
                ),
            }],
            proposed_actions=proposed,
        )


class ConversationManagerAgent(BaseAgent):
    agent_id = "agent_conversation_manager"

    def _execute(self, inputs: dict) -> AgentResult:
        from conversation.engine import get_conversation_engine
        ce = get_conversation_engine()
        analytics = ce.analytics()
        active = analytics.get("active_threads", 0)
        total_msg = analytics.get("total_messages", 0)
        return AgentResult(
            agent_id=self.agent_id,
            findings=[{
                "analytics": analytics,
                "advisory": (
                    f"Conversation analytics: {analytics.get('total_threads', 0)} threads total, "
                    f"{active} active, {total_msg} messages. "
                    f"Avg {analytics.get('avg_turns_per_thread', '—')} turns per thread."
                ),
            }],
            proposed_actions=[],
        )


class PresenceAgent(BaseAgent):
    agent_id = "agent_presence"

    def _execute(self, inputs: dict) -> AgentResult:
        from presence.engine import get_presence_engine
        pe = get_presence_engine()
        state = pe.get_state()
        mode = state.get("mode", "unknown")
        config = pe.adaptive_config()
        focus = state.get("focus", {})
        return AgentResult(
            agent_id=self.agent_id,
            findings=[{
                "state": state,
                "adaptive_config": config,
                "advisory": (
                    f"Current mode: {mode}. "
                    f"Notification level: {config.get('notification_level', 'medium')}. "
                    f"Focus active: {focus.get('enabled', False)}. "
                    f"Voice sensitivity: {config.get('voice_sensitivity', 'medium')}."
                ),
            }],
            proposed_actions=[],
        )


_REGISTRY = {
    "voice_concierge": VoiceConciergeAgent,
    "executive_assistant": ExecutiveAssistantAgent,
    "notification": NotificationAgent,
    "desktop_ops": DesktopOperationsAgent,
    "conversation_manager": ConversationManagerAgent,
    "presence": PresenceAgent,
}


def get_voice_agent(key: str):
    global _instances
    if key not in _REGISTRY:
        raise KeyError(f"Unknown voice agent: {key}")
    if key not in _instances:
        _instances[key] = _REGISTRY[key]()
    return _instances[key]


def list_voice_agents() -> list:
    return [
        {
            "key": k,
            "agent_id": _REGISTRY[k].agent_id,
            "name": k.replace("_", " ").title(),
        }
        for k in _REGISTRY
    ]
