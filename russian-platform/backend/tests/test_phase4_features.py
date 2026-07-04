"""Phase 4 tests: content packs, account backup/restore, encryption,
global search, local AI providers."""
import json

import pytest

from app.services.account_backup import decrypt_backup, encrypt_backup
from app.services.content_packs import (
    build_pack,
    checksum,
    install_pack,
    rollback_pack,
    validate_pack,
)
from tests.test_lessons import _pass_lesson


def _mini_pack(name="test-pack", version="1.0.0", signing_key=None):
    """A small self-consistent pack built by hand (not from the DB)."""
    from app.services.content_packs import sign
    from app.services.vocab_factory import build_entry

    entry = build_entry(("тень", "n", "shadow", "nature", "B1", {"gender": "f"}))
    entry["examples"] = [["В тени́ прохла́дно.", "It is cool in the shade."]]
    entry["relations"] = []
    content = {
        "language_meta": {"code": "ru"},
        "vocabulary": [entry],
        "texts": [{
            "slug": "pack-text", "title": "Тест", "title_translation": "Test",
            "kind": "story", "cefr_level": "A1", "summary": "Pack test text.",
            "sentences": [
                {"ru": "Я до́ма.", "en": "I am home."},
                {"ru": "Ты до́ма.", "en": "You are home."},
                {"ru": "Мы до́ма.", "en": "We are home."},
            ],
        }],
        "grammar_topics": [],
        "scenarios": [],
    }
    digest = checksum(content)
    manifest = {"name": name, "version": version, "format": 1,
                "language": "ru", "counts": {}, "checksum": digest}
    if signing_key:
        manifest["signature"] = sign(digest, signing_key)
    return {"manifest": manifest, "content": content}


class TestContentPacks:
    def test_build_pack_from_database(self, db_session):
        pack = build_pack(db_session, "ru-core", "1.0.0")
        assert pack["manifest"]["counts"]["vocabulary"] >= 600
        assert pack["manifest"]["counts"]["texts"] >= 8
        assert pack["manifest"]["checksum"] == checksum(pack["content"])

    def test_install_and_provenance(self, db_session, client, auth_headers):
        record = install_pack(db_session, _mini_pack())
        assert record.version == "1.0.0"
        assert len(record.row_ids["lexemes"]) == 1
        assert len(record.row_ids["texts"]) == 1
        found = client.get("/api/v1/vocabulary?q=shadow", headers=auth_headers).json()
        assert found["total"] == 1
        # Inflected forms of pack words are indexed too.
        form = client.get("/api/v1/vocabulary?q=тенью", headers=auth_headers).json()
        assert form["form_matches"]

    def test_corrupted_pack_rejected(self, db_session):
        pack = _mini_pack()
        pack["content"]["vocabulary"][0]["translation"] = "tampered"
        report = validate_pack(pack, db_session)
        assert not report.ok
        assert "checksum" in report.errors[0]

    def test_bad_signature_rejected(self, db_session):
        pack = _mini_pack(signing_key="right-key")
        report = validate_pack(pack, db_session, signing_key="wrong-key")
        assert not report.ok
        assert "signature" in report.errors[0].lower()

    def test_good_signature_accepted(self, db_session):
        pack = _mini_pack(signing_key="shared-key")
        report = validate_pack(pack, db_session, signing_key="shared-key")
        assert report.ok, report.errors

    def test_same_version_reinstall_rejected(self, db_session):
        install_pack(db_session, _mini_pack())
        with pytest.raises(ValueError, match="not newer"):
            install_pack(db_session, _mini_pack())

    def test_incremental_upgrade(self, db_session):
        install_pack(db_session, _mini_pack())
        upgrade = _mini_pack(version="1.1.0")
        # v1.1 adds one more word; existing content is skipped, not duplicated.
        from app.services.content_packs import checksum as _checksum
        from app.services.vocab_factory import build_entry

        extra = build_entry(("мель", "n", "shoal", "nature", "C1", {"gender": "f"}))
        extra["examples"] = []
        extra["relations"] = []
        upgrade["content"]["vocabulary"].append(extra)
        upgrade["manifest"]["checksum"] = _checksum(upgrade["content"])
        record = install_pack(db_session, upgrade)
        assert record.version == "1.1.0"
        assert len(record.row_ids["lexemes"]) == 2  # merged provenance

    def test_rollback_refuses_when_cards_exist_then_forces(
        self, db_session, client, auth_headers
    ):
        install_pack(db_session, _mini_pack())
        found = client.get("/api/v1/vocabulary?q=shadow", headers=auth_headers).json()
        client.post("/api/v1/library/add-word",
                    json={"lexeme_id": found["items"][0]["id"]},
                    headers=auth_headers)
        with pytest.raises(ValueError, match="SRS cards"):
            rollback_pack(db_session, "test-pack")
        removed = rollback_pack(db_session, "test-pack", force=True)
        assert removed["lexemes"] == 1 and removed["cards"] == 1
        gone = client.get("/api/v1/vocabulary?q=shadow", headers=auth_headers).json()
        assert gone["total"] == 0


class TestAccountBackup:
    def _make_progress(self, client, auth_headers):
        for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                     "a0-03-stress", "a0-04-greetings"):
            _pass_lesson(client, auth_headers, slug)
        queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
        for card in queue["cards"][:3]:
            client.post(f"/api/v1/reviews/{card['card_id']}", json={"rating": 3},
                        headers=auth_headers)
        client.put("/api/v1/library/texts/repka/bookmark",
                   json={"sentence_index": 5}, headers=auth_headers)

    def test_export_roundtrip_into_fresh_account(self, client, auth_headers):
        self._make_progress(client, auth_headers)
        me_before = client.get("/api/v1/auth/me", headers=auth_headers).json()
        backup = client.post("/api/v1/account/export", json={},
                             headers=auth_headers).json()
        assert len(backup["cards"]) == 8
        assert len(backup["completions"]) == 4
        assert backup["bookmarks"][0]["text_slug"] == "repka"

        other = client.post("/api/v1/auth/register", json={
            "email": "fresh@example.com", "password": "password123",
            "display_name": "Fresh"}).json()
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        result = client.post("/api/v1/account/import",
                             json={"backup": backup},
                             headers=other_headers).json()
        assert result["cards_created"] == 8
        assert result["completions_added"] == 4
        assert result["achievements_added"] >= 1
        me_after = client.get("/api/v1/auth/me", headers=other_headers).json()
        assert me_after["xp"] == me_before["xp"]
        # Restored lesson progress unlocks the same next lesson.
        courses = client.get("/api/v1/lessons/courses", headers=other_headers).json()
        a0 = next(c for c in courses if c["slug"] == "a0-foundations")
        assert a0["lessons"][4]["unlocked"] is True

    def test_restore_never_regresses(self, client, auth_headers):
        self._make_progress(client, auth_headers)
        backup = client.post("/api/v1/account/export", json={},
                             headers=auth_headers).json()
        # Keep studying after the backup...
        queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
        client.post(f"/api/v1/reviews/{queue['cards'][0]['card_id']}",
                    json={"rating": 4}, headers=auth_headers)
        xp_now = client.get("/api/v1/auth/me", headers=auth_headers).json()["xp"]
        # ...then restore the OLD backup onto the same account.
        client.post("/api/v1/account/import", json={"backup": backup},
                    headers=auth_headers)
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        assert me["xp"] >= xp_now  # progress never lost

    def test_encrypted_backup_roundtrip(self, client, auth_headers):
        self._make_progress(client, auth_headers)
        envelope = client.post("/api/v1/account/export",
                               json={"password": "correct horse"},
                               headers=auth_headers).json()
        assert envelope["encrypted"] is True
        assert "cards" not in json.dumps(envelope)[:200]

        wrong = client.post("/api/v1/account/import",
                            json={"backup": envelope, "password": "wrong"},
                            headers=auth_headers)
        assert wrong.status_code == 400

        ok = client.post("/api/v1/account/import",
                         json={"backup": envelope, "password": "correct horse"},
                         headers=auth_headers)
        assert ok.status_code == 200

    def test_encrypt_decrypt_unit(self):
        data = {"format": 1, "cards": [{"lemma": "дом"}]}
        envelope = encrypt_backup(data, "пароль")
        assert decrypt_backup(envelope, "пароль") == data
        with pytest.raises(ValueError):
            decrypt_backup(envelope, "не тот пароль")


class TestGlobalSearch:
    def test_search_across_types(self, client, auth_headers):
        results = client.get("/api/v1/account/search?q=погода",
                             headers=auth_headers).json()["results"]
        assert any(w["lemma"] == "погода" for w in results["words"])
        assert any(t["slug"] == "pogoda-v-rossii" for t in results["texts"])

    def test_inflected_form_search(self, client, auth_headers):
        results = client.get("/api/v1/account/search?q=живу",
                             headers=auth_headers).json()["results"]
        assert results["words"][0]["lemma"] == "жить"
        assert results["words"][0]["match"].startswith("form:")

    def test_fuzzy_and_grammar(self, client, auth_headers):
        results = client.get("/api/v1/account/search?q=aspect",
                             headers=auth_headers).json()["results"]
        assert any("aspect" in g["title"].lower() for g in results["grammar"])
        fuzzy = client.get("/api/v1/account/search?q=кнега",
                           headers=auth_headers).json()["results"]
        assert fuzzy["words"][0]["match"] == "fuzzy"

    def test_empty_query(self, client, auth_headers):
        results = client.get("/api/v1/account/search?q=%20",
                             headers=auth_headers).json()
        assert results["results"] == {}


class TestLocalProviders:
    def test_llama_provider_selected_when_healthy(self, monkeypatch):
        import httpx

        from app.core.config import get_settings
        from app.services.llm import LocalLlamaProvider, get_llm_provider

        settings = get_settings()
        monkeypatch.setattr(settings, "llm_provider", "llama-cpp")
        monkeypatch.setattr(settings, "llama_url", "http://localhost:9999")
        monkeypatch.setattr(
            httpx, "get",
            lambda url, timeout: type("R", (), {"status_code": 200})(),
        )
        provider = get_llm_provider()
        assert isinstance(provider, LocalLlamaProvider)

    def test_llama_degrades_to_offline_when_unreachable(self, monkeypatch):
        from app.core.config import get_settings
        from app.services.llm import OfflineProvider, get_llm_provider

        settings = get_settings()
        monkeypatch.setattr(settings, "llm_provider", "llama-cpp")
        monkeypatch.setattr(settings, "llama_url", "http://localhost:1")
        provider = get_llm_provider()
        assert isinstance(provider, OfflineProvider)

    def test_llama_completion_wire_format(self, monkeypatch):
        import httpx

        from app.services.llm import LocalLlamaProvider

        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json

            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"choices": [{"message": {"content": "Приве́т!"}}]}

            return Response()

        monkeypatch.setattr(httpx, "post", fake_post)
        provider = LocalLlamaProvider("http://localhost:8080")
        reply = provider.complete("system prompt", [{"role": "user", "content": "hi"}])
        assert reply == "Приве́т!"
        assert captured["url"].endswith("/v1/chat/completions")
        assert captured["json"]["messages"][0]["role"] == "system"

    def test_gguf_degrades_without_package(self, monkeypatch):
        from app.core.config import get_settings
        from app.services.llm import OfflineProvider, get_llm_provider

        settings = get_settings()
        monkeypatch.setattr(settings, "llm_provider", "llama-gguf")
        monkeypatch.setattr(settings, "llama_model_path", "/nonexistent.gguf")
        provider = get_llm_provider()
        assert isinstance(provider, OfflineProvider)
