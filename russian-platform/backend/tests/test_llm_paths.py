"""Generative-path tests using a stub provider — no network required."""
from app.services.conversation_engine import ConversationEngine
from app.services.llm import LLMProvider, OfflineProvider
from app.services.tutor import TutorEngine, tutor_system_prompt

import pytest


class StubProvider(LLMProvider):
    """Returns a canned reply in the platform's ---/### wire format."""

    def __init__(self, reply: str):
        self._reply = reply
        self.last_system: str | None = None
        self.last_messages: list[dict] | None = None

    @property
    def is_generative(self) -> bool:
        return True

    def complete(self, system, messages, max_tokens=1024):
        self.last_system = system
        self.last_messages = messages
        return self._reply


CANNED = (
    "Отли́чно! А где ты живёшь?\n---\nGreat! And where do you live?\n###\n"
    '[{"error": "я жить", "correction": "я живу́", '
    '"explanation": "First person needs -у"}]'
)


def test_tutor_reply_parses_wire_format(db_session, client, auth_headers):
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    provider = StubProvider(CANNED)
    engine = TutorEngine(provider)
    reply = engine.reply(db_session, me["id"], "socratic", "warm",
                         [{"role": "user", "text": "Привет"}], "я жить в Москве")
    assert reply["text"] == "Отли́чно! А где ты живёшь?"
    assert reply["translation"] == "Great! And where do you live?"
    assert reply["corrections"][0]["correction"] == "я живу́"
    # The system prompt embeds the learner profile and the mode.
    assert "CEFR A0" in provider.last_system
    assert "asking questions" in provider.last_system.lower()
    assert provider.last_messages[-1]["content"] == "я жить в Москве"


def test_tutor_reply_survives_malformed_corrections(db_session, client, auth_headers):
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    engine = TutorEngine(StubProvider("Приве́т!\n---\nHi!\n###\nnot-json"))
    reply = engine.reply(db_session, me["id"], "free", "warm", [], "привет")
    assert reply["text"] == "Приве́т!"
    assert reply["corrections"] == []


def test_conversation_engine_llm_path(db_session, client, auth_headers):
    from sqlalchemy import select

    from app.models import ConversationSession, Scenario

    scenario = db_session.scalar(select(Scenario).where(Scenario.slug == "cafe-order"))
    session = ConversationSession(user_id=1, scenario_id=scenario.id, memory={})
    engine = ConversationEngine(StubProvider(CANNED))
    reply = engine.reply(scenario, session, [], "Я хочу кофе")
    assert reply["text"] == "Отли́чно! А где ты живёшь?"
    assert reply["corrections"]


def test_offline_provider_refuses_free_generation():
    provider = OfflineProvider()
    assert provider.is_generative is False
    with pytest.raises(RuntimeError):
        provider.complete("system", [])


def test_tutor_system_prompt_targets_weaknesses():
    profile = {
        "cefr": "A2", "known_words": 120,
        "weak_grammar": [{"slug": "dative-case", "title": "Dative Case", "mastery": 0.3}],
        "weak_words": [{"lemma": "врач", "translation": "doctor"}],
        "total_lapses": 5,
    }
    prompt = tutor_system_prompt(profile, "debate", "strict")
    assert "Dative Case" in prompt
    assert "врач" in prompt
    assert "NEVER give the answer immediately" in prompt
