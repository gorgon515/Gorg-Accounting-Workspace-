"""Edge-branch tests for backup restore and content packs."""
import pytest

from app.services.content_packs import build_pack, install_pack, rollback_pack
from tests.test_phase4_features import _mini_pack
from tests.test_lessons import _pass_lesson


class TestRestoreEdges:
    def test_unknown_format_rejected(self, client, auth_headers):
        response = client.post("/api/v1/account/import",
                               json={"backup": {"format": 99}},
                               headers=auth_headers)
        assert response.status_code == 422

    def test_missing_content_is_skipped_not_fatal(self, client, auth_headers):
        backup = {
            "format": 1,
            "profile": {"xp": 10},
            "cards": [{"lemma": "несуществующее", "card_type": "vocabulary",
                       "direction": "recognition", "stability": 5.0,
                       "difficulty": 5.0, "reps": 3, "lapses": 0,
                       "state": "review", "due_at": "2026-01-01T00:00:00+00:00",
                       "last_reviewed_at": None}],
            "completions": [{"lesson_slug": "no-such-lesson", "score": 1.0,
                             "passed": True,
                             "completed_at": "2026-01-01T00:00:00+00:00"}],
            "grammar_mastery": [{"topic_slug": "no-such-topic", "mastery": 0.9,
                                 "attempts": 5, "correct": 5}],
            "achievements": [{"slug": "no-such-badge",
                              "earned_at": "2026-01-01T00:00:00+00:00"}],
            "bookmarks": [{"text_slug": "no-such-text", "sentence_index": 3}],
            "exam_results": [],
        }
        result = client.post("/api/v1/account/import", json={"backup": backup},
                             headers=auth_headers).json()
        assert result["cards_created"] == 0
        assert result["completions_added"] == 0
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        assert me["xp"] == 10  # profile merge still applied

    def test_mastery_and_bookmark_merge_takes_stronger(self, client, auth_headers):
        # Establish local mastery + bookmark first.
        client.post("/api/v1/grammar/topics/gender/drills",
                    json={"answers": {"gen1": "f"}}, headers=auth_headers)
        client.put("/api/v1/library/texts/repka/bookmark",
                   json={"sentence_index": 2}, headers=auth_headers)
        backup = {
            "format": 1, "profile": {},
            "cards": [], "completions": [],
            "grammar_mastery": [{"topic_slug": "gender", "mastery": 0.95,
                                 "attempts": 40, "correct": 38}],
            "achievements": [],
            "bookmarks": [{"text_slug": "repka", "sentence_index": 7}],
            "exam_results": [{"kind": "level", "level": "A1", "seed": "s1",
                              "score": 0.9, "passed": True, "sections": {},
                              "taken_at": "2026-01-01T00:00:00+00:00"}],
        }
        client.post("/api/v1/account/import", json={"backup": backup},
                    headers=auth_headers)
        topics = client.get("/api/v1/grammar/topics", headers=auth_headers).json()
        gender = next(t for t in topics if t["slug"] == "gender")
        assert gender["mastery"] >= 0.95
        text = client.get("/api/v1/library/texts/repka", headers=auth_headers).json()
        assert text["bookmark"] == 7
        results = client.get("/api/v1/exams/results", headers=auth_headers).json()
        assert len(results) == 1
        # Re-import: exam result deduplicated.
        client.post("/api/v1/account/import", json={"backup": backup},
                    headers=auth_headers)
        assert len(client.get("/api/v1/exams/results",
                              headers=auth_headers).json()) == 1


class TestPackEdges:
    def test_pack_installs_new_language_row(self, db_session):
        pack = _mini_pack(name="de-starter")
        pack["manifest"]["language"] = "de"
        pack["content"]["language_meta"] = {
            "code": "de", "name_english": "German", "name_native": "Deutsch",
            "script": "Latin", "metadata_json": {},
        }
        from app.services.content_packs import checksum

        pack["manifest"]["checksum"] = checksum(pack["content"])
        record = install_pack(db_session, pack)
        assert record.language == "de"
        from app.models import Language
        from sqlalchemy import select

        german = db_session.scalar(select(Language).where(Language.code == "de"))
        assert german is not None and german.name_native == "Deutsch"
        rollback_pack(db_session, "de-starter")

    def test_rollback_without_cards_is_clean(self, db_session):
        install_pack(db_session, _mini_pack(name="clean-pack"))
        removed = rollback_pack(db_session, "clean-pack")
        assert removed == {"lexemes": 1, "texts": 1, "grammar_topics": 0,
                           "scenarios": 0, "cards": 0}

    def test_rollback_unknown_pack(self, db_session):
        with pytest.raises(LookupError):
            rollback_pack(db_session, "ghost-pack")

    def test_signed_build_roundtrip(self, db_session):
        pack = build_pack(db_session, "ru-signed", "1.0.0", signing_key="k1")
        assert "signature" in pack["manifest"]
        from app.services.content_packs import validate_pack

        report = validate_pack(pack, db_session, signing_key="k1")
        # Everything already installed → warnings, but structurally valid.
        assert not any("signature" in e for e in report.errors)

    def test_manifest_field_missing(self, db_session):
        from app.services.content_packs import validate_pack

        report = validate_pack({"manifest": {"name": "x"}, "content": {}}, db_session)
        assert not report.ok


class TestBackupAfterFullFlow:
    def test_export_covers_exams_and_grammar(self, client, auth_headers, db_session):
        from app.services.exams import build_level_exam

        _pass_lesson(client, auth_headers, "a0-01-cyrillic-friends")
        exam = build_level_exam(db_session, "A1", "backup-seed")
        answers = {q["id"]: q["_answer"]
                   for qs in exam["sections"].values() for q in qs}
        client.post("/api/v1/exams/level/A1/submit",
                    json={"seed": "backup-seed", "answers": answers},
                    headers=auth_headers)
        backup = client.post("/api/v1/account/export", json={},
                             headers=auth_headers).json()
        assert backup["exam_results"][0]["passed"] is True
        assert backup["profile"]["cefr_estimate"] == "A1"
