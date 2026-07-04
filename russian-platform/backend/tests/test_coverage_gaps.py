"""Targeted tests for the generative and utility paths not exercised by
the feature suites (content generation, provider selection, token edge
cases, LLM-enriched writing)."""
import pytest

from app.core import security
from app.services.content_gen import build_cloze_drill, build_quiz, generate_story
from app.services.llm import AnthropicProvider, OfflineProvider, get_llm_provider
from tests.test_lessons import _pass_lesson
from tests.test_llm_paths import StubProvider


class TestContentGeneration:
    def _enroll(self, client, auth_headers):
        for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                     "a0-03-stress", "a0-04-greetings"):
            _pass_lesson(client, auth_headers, slug)
        queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
        for card in queue["cards"][:4]:
            client.post(f"/api/v1/reviews/{card['card_id']}", json={"rating": 2},
                        headers=auth_headers)

    def test_cloze_drill_from_learner_examples(self, client, auth_headers, db_session):
        self._enroll(client, auth_headers)
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        drill = build_cloze_drill(db_session, me["id"], size=4, seed=7)
        assert drill["type"] == "cloze_drill"
        for q in drill["questions"]:
            assert "____" in q["sentence"]
            assert q["answer"] not in q["sentence"]

    def test_quiz_deterministic_with_seed(self, client, auth_headers, db_session):
        self._enroll(client, auth_headers)
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        first = build_quiz(db_session, me["id"], size=5, seed=42)
        second = build_quiz(db_session, me["id"], size=5, seed=42)
        assert first == second

    def test_story_generation_with_stub_provider(self):
        stub = StubProvider(
            "Жил-был кот.\n---\nOnce there was a cat.\n###\n"
            '[{"q": "Кто жил?", "a": "кот"}]'
        )
        story = generate_story(stub, "A1", ["кот", "дом"], topic="кот")
        assert story["text"] == "Жил-был кот."
        assert story["translation"] == "Once there was a cat."
        assert story["questions"][0]["a"] == "кот"

    def test_story_with_malformed_questions_degrades(self):
        stub = StubProvider("Текст.\n---\nText.\n###\nnot json")
        story = generate_story(stub, "A1", [])
        assert story["questions"] == []

    def test_story_requires_generative(self):
        with pytest.raises(LookupError):
            generate_story(OfflineProvider(), "A1", [])


class TestProviderSelection:
    def test_offline_by_default(self):
        assert isinstance(get_llm_provider(), OfflineProvider)

    def test_anthropic_when_configured(self, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "llm_provider", "anthropic")
        monkeypatch.setattr(settings, "anthropic_api_key", "sk-test")
        provider = get_llm_provider()
        assert isinstance(provider, AnthropicProvider)
        assert provider.is_generative


class TestSecurityEdges:
    def test_invalid_token_returns_none(self):
        assert security.decode_access_token("garbage.token.here") is None

    def test_long_password_truncated_consistently(self):
        long_password = "я" * 200
        hashed = security.hash_password(long_password)
        assert security.verify_password(long_password, hashed)

    def test_malformed_hash_rejected(self):
        assert security.verify_password("x", "not-a-bcrypt-hash") is False


class TestWritingWithLLM:
    def test_analyze_merges_llm_corrections(self, client, auth_headers, monkeypatch):
        from app.api.routes import writing as writing_route

        stub = StubProvider(
            '{"quality_score": 0.8, "corrections": '
            '[{"error": "я жить", "correction": "я живу", '
            '"explanation": "conjugate"}]}'
        )
        monkeypatch.setattr(writing_route, "get_llm_provider", lambda: stub)
        result = client.post("/api/v1/writing/analyze",
                             json={"kind": "journal", "text": "Я жить в Москве."},
                             headers=auth_headers).json()
        assert result["llm_feedback_available"] is True
        assert result["llm_corrections"][0]["correction"] == "я живу"


class TestImportCLIs:
    def test_vocabulary_cli_dry_run(self, tmp_path, monkeypatch):
        import json

        from tools import import_vocabulary

        dataset = tmp_path / "words.json"
        dataset.write_text(json.dumps(
            [["тень", "n", "shadow", "nature", "B1", {"gender": "f"}]],
            ensure_ascii=False,
        ), encoding="utf-8")
        assert import_vocabulary.main([str(dataset)]) == 0

    def test_vocabulary_cli_rejects_bad_data(self, tmp_path):
        import json

        from tools import import_vocabulary

        dataset = tmp_path / "bad.json"
        dataset.write_text(json.dumps([["собрание", "n", "meeting", "work", "B1"]],
                                      ensure_ascii=False), encoding="utf-8")
        assert import_vocabulary.main([str(dataset)]) == 1

    def test_texts_cli_help(self, capsys):
        from tools import import_texts

        assert import_texts.main([]) == 0
        assert "Usage" in capsys.readouterr().out
