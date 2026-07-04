"""Phase 2 feature tests: SRS planner, library, tutor, quests, trends,
dictionary upgrades, profile settings, generated courses."""
from datetime import datetime, timedelta, timezone

from app.services import srs_planner
from app.services.srs_engine import interval_for_retention
from tests.test_lessons import _pass_lesson


# ---------------------------------------------------------------- SRS planner
class TestSrsPlanner:
    def test_adaptive_retention_defaults_with_little_history(self, db_session, client, auth_headers):
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        assert srs_planner.adaptive_target_retention(db_session, me["id"]) == 0.9

    def test_adaptive_retention_rises_for_struggling_learner(self, db_session, client, auth_headers):
        from app.models import ReviewLog

        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        for i in range(30):
            db_session.add(
                ReviewLog(card_id=1, user_id=me["id"], rating=1 if i % 2 else 3,
                          elapsed_days=1, predicted_retention=0.5,
                          stability_before=1, stability_after=1, interval_days=1)
            )
        db_session.commit()
        assert srs_planner.adaptive_target_retention(db_session, me["id"]) == 0.93

    def test_higher_retention_means_shorter_interval(self):
        assert interval_for_retention(10, 0.93) < interval_for_retention(10, 0.9)

    def test_forecast_counts_due_cards(self, db_session, client, auth_headers):
        _pass_lesson(client, auth_headers, "a0-01-cyrillic-friends")
        _pass_lesson(client, auth_headers, "a0-02-cyrillic-new")
        _pass_lesson(client, auth_headers, "a0-03-stress")
        _pass_lesson(client, auth_headers, "a0-04-greetings")
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        forecast = srs_planner.forecast(db_session, me["id"], days=7)
        assert len(forecast) == 7
        assert forecast[0]["due"] == 8  # new cards land due immediately

    def test_forecast_endpoint(self, client, auth_headers):
        response = client.get("/api/v1/reviews/forecast?days=14", headers=auth_headers)
        body = response.json()
        assert len(body["forecast"]) == 14
        assert 0.85 <= body["target_retention"] <= 0.95

    def test_balance_leaves_near_dates_alone(self, db_session, client, auth_headers):
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        soon = datetime.now(timezone.utc) + timedelta(days=1)
        assert srs_planner.balance_due_date(db_session, me["id"], soon) == soon


# ------------------------------------------------------------------- library
class TestLibrary:
    def test_texts_listed_with_metadata(self, client, auth_headers):
        texts = client.get("/api/v1/library/texts", headers=auth_headers).json()
        assert len(texts) >= 8
        slugs = {t["slug"] for t in texts}
        assert "repka" in slugs
        assert all(t["sentence_count"] > 0 for t in texts)

    def test_cefr_filter(self, client, auth_headers):
        texts = client.get("/api/v1/library/texts?cefr=B1", headers=auth_headers).json()
        assert texts and all(t["cefr_level"] == "B1" for t in texts)

    def test_text_detail_has_glossary(self, client, auth_headers):
        text = client.get("/api/v1/library/texts/moya-semya", headers=auth_headers).json()
        assert len(text["sentences"]) == 11
        assert "врач" in text["glossary"]
        assert text["glossary"]["врач"]["translation"] == "doctor"

    def test_add_word_from_reading(self, client, auth_headers):
        text = client.get("/api/v1/library/texts/moya-semya", headers=auth_headers).json()
        lexeme_id = text["glossary"]["врач"]["id"]
        first = client.post("/api/v1/library/add-word", json={"lexeme_id": lexeme_id},
                            headers=auth_headers)
        assert first.status_code == 201 and first.json()["created"] is True
        again = client.post("/api/v1/library/add-word", json={"lexeme_id": lexeme_id},
                            headers=auth_headers)
        assert again.json()["created"] is False

    def test_bookmark_roundtrip(self, client, auth_headers):
        client.put("/api/v1/library/texts/repka/bookmark",
                   json={"sentence_index": 4}, headers=auth_headers)
        text = client.get("/api/v1/library/texts/repka", headers=auth_headers).json()
        assert text["bookmark"] == 4

    def test_dictation_scoring(self, client, auth_headers):
        perfect = client.post(
            "/api/v1/library/texts/repka/dictation",
            json={"sentence_index": 0, "typed_text": "посадил дед репку"},
            headers=auth_headers,
        ).json()
        assert perfect["overall_score"] == 100.0
        flawed = client.post(
            "/api/v1/library/texts/repka/dictation",
            json={"sentence_index": 0, "typed_text": "посадил репку"},
            headers=auth_headers,
        ).json()
        assert flawed["overall_score"] < 100.0

    def test_dictation_bad_index(self, client, auth_headers):
        response = client.post(
            "/api/v1/library/texts/repka/dictation",
            json={"sentence_index": 99, "typed_text": "x"},
            headers=auth_headers,
        )
        assert response.status_code == 400


# --------------------------------------------------------------------- tutor
class TestTutor:
    def test_offline_plan_is_personalized(self, client, auth_headers):
        for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                     "a0-03-stress", "a0-04-greetings"):
            _pass_lesson(client, auth_headers, slug)
        queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
        client.post(f"/api/v1/reviews/{queue['cards'][0]['card_id']}",
                    json={"rating": 1}, headers=auth_headers)
        plan = client.get("/api/v1/conversation/tutor/plan", headers=auth_headers).json()
        assert plan["profile"]["cefr"] == "A0"
        assert plan["speaking_prompts"]  # built from the learner's weak words
        assert plan["writing_prompt"].startswith("Напиши́те")

    def test_chat_requires_generative_provider(self, client, auth_headers):
        response = client.post(
            "/api/v1/conversation/tutor",
            json={"text": "Привет!", "mode": "socratic"},
            headers=auth_headers,
        )
        assert response.status_code == 409

    def test_invalid_mode_rejected(self, client, auth_headers):
        response = client.post(
            "/api/v1/conversation/tutor",
            json={"text": "Привет!", "mode": "hypnosis"},
            headers=auth_headers,
        )
        assert response.status_code == 422


# -------------------------------------------------------------------- quests
class TestQuests:
    def test_quests_track_todays_progress(self, client, auth_headers):
        _pass_lesson(client, auth_headers, "a0-01-cyrillic-friends")
        quests = client.get("/api/v1/gamification/quests", headers=auth_headers).json()
        lesson_quest = next(q for q in quests if q["slug"] == "lesson-1")
        assert lesson_quest["complete"] is True
        assert lesson_quest["claimed"] is False

    def test_claim_grants_xp_once(self, client, auth_headers):
        _pass_lesson(client, auth_headers, "a0-01-cyrillic-friends")
        before = client.get("/api/v1/auth/me", headers=auth_headers).json()["xp"]
        first = client.post("/api/v1/gamification/quests/lesson-1/claim",
                            headers=auth_headers)
        assert first.status_code == 200
        assert first.json()["total_xp"] == before + 40
        second = client.post("/api/v1/gamification/quests/lesson-1/claim",
                             headers=auth_headers)
        assert second.status_code == 409

    def test_incomplete_quest_cannot_be_claimed(self, client, auth_headers):
        response = client.post("/api/v1/gamification/quests/reviews-20/claim",
                               headers=auth_headers)
        assert response.status_code == 409

    def test_achievement_collection_with_rarity(self, client, auth_headers):
        achievements = client.get("/api/v1/gamification/achievements",
                                  headers=auth_headers).json()
        assert len(achievements) >= 10
        rarities = {a["rarity"] for a in achievements}
        assert "legendary" in rarities and "common" in rarities


# ------------------------------------------------------------------ analytics
class TestTrends:
    def test_trends_empty_user(self, client, auth_headers):
        trends = client.get("/api/v1/analytics/trends", headers=auth_headers).json()
        assert trends["heatmap"] == {} or isinstance(trends["heatmap"], dict)
        assert trends["fluency_estimate"] is None

    def test_trends_after_activity(self, client, auth_headers):
        for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                     "a0-03-stress", "a0-04-greetings"):
            _pass_lesson(client, auth_headers, slug)
        queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
        for card in queue["cards"][:3]:
            client.post(f"/api/v1/reviews/{card['card_id']}", json={"rating": 3},
                        headers=auth_headers)
        trends = client.get("/api/v1/analytics/trends", headers=auth_headers).json()
        assert sum(trends["heatmap"].values()) >= 7
        assert trends["skills"]["vocabulary"] == 1.0
        assert trends["fluency_estimate"]["target_level"] == "B2"
        assert trends["velocity"]


# ------------------------------------------------------------------ dictionary
class TestDictionaryUpgrades:
    def test_fuzzy_search_catches_typo(self, client, auth_headers):
        body = client.get("/api/v1/vocabulary?q=кнега", headers=auth_headers).json()
        assert body["total"] == 0
        assert any(f["lemma"] == "книга" for f in body["fuzzy"])

    def test_topic_filter_and_listing(self, client, auth_headers):
        topics = client.get("/api/v1/vocabulary/topics", headers=auth_headers).json()
        assert any(t["topic"] == "food" for t in topics)
        food = client.get("/api/v1/vocabulary?topic=food", headers=auth_headers).json()
        assert food["total"] >= 30
        assert all(item["topic"] == "food" for item in food["items"])

    def test_verb_pairs(self, client, auth_headers):
        pairs = client.get("/api/v1/vocabulary/verb-pairs", headers=auth_headers).json()
        assert len(pairs) >= 30
        speak = next(p for p in pairs if p["imperfective"] == "говори́ть")
        assert speak["perfective"] == "сказа́ть"

    def test_expanded_vocabulary_size(self, client, auth_headers):
        body = client.get("/api/v1/vocabulary", headers=auth_headers).json()
        assert body["total"] >= 570


# ------------------------------------------------------------------- settings
class TestProfileSettings:
    def test_patch_profile_and_preferences_merge(self, client, auth_headers):
        updated = client.patch(
            "/api/v1/auth/me",
            json={"ui_immersion_ratio": 0.5,
                  "preferences": {"font_scale": 1.25}},
            headers=auth_headers,
        ).json()
        assert updated["ui_immersion_ratio"] == 0.5
        assert updated["preferences"]["font_scale"] == 1.25

        updated = client.patch(
            "/api/v1/auth/me",
            json={"preferences": {"high_contrast": True}},
            headers=auth_headers,
        ).json()
        assert updated["preferences"] == {"font_scale": 1.25, "high_contrast": True}

    def test_invalid_immersion_rejected(self, client, auth_headers):
        response = client.patch("/api/v1/auth/me", json={"ui_immersion_ratio": 1.5},
                                headers=auth_headers)
        assert response.status_code == 422


# ------------------------------------------------------------- generated курс
class TestGeneratedCourses:
    def test_catalog_size_and_ordering(self, client, auth_headers):
        courses = client.get("/api/v1/lessons/courses", headers=auth_headers).json()
        slugs = [c["slug"] for c in courses]
        assert slugs[0] == "a0-foundations"
        assert slugs[1] == "a1-survival"
        assert len(courses) >= 14  # Phase 3 multi-track catalog
        total_lessons = sum(len(c["lessons"]) for c in courses)
        assert total_lessons >= 300  # Phase 3 acceptance criterion

    def test_vocab_lessons_have_valid_answer_keys(self):
        from app.seed.course_builder import build_generated_courses
        from app.seed.wordlist import W
        from app.services.morphology import strip_stress

        lemmas = {strip_stress(w[0]) for w in W}
        courses = {c["slug"]: c for c in build_generated_courses()}
        for slug in ("a2-everyday", "b1-wider-world"):
            for lesson in courses[slug]["lessons"]:
                if "-review-" in lesson["slug"]:
                    continue  # checkpoints resample earlier questions
                assert lesson["new_lemmas"]
                assert set(lesson["new_lemmas"]) <= lemmas
                for block in lesson["blocks"]:
                    if block["type"] == "mastery_test":
                        assert block["questions"]
                        for q in block["questions"]:
                            assert q["answer"] in lemmas

    def test_every_generated_lesson_is_gradeable(self):
        """No placeholder lessons: every lesson in every family carries at
        least one machine-checkable question with a non-empty answer."""
        from app.seed.course_builder import build_generated_courses

        for course in build_generated_courses():
            assert course["lessons"], course["slug"]
            for lesson in course["lessons"]:
                questions = [q for b in lesson["blocks"]
                             if b["type"] in ("exercise", "mastery_test")
                             for q in b["questions"]]
                assert questions, lesson["slug"]
                for q in questions:
                    assert q["answer"].strip(), (lesson["slug"], q["id"])

    def test_case_drill_answers_match_morphology(self):
        from app.seed.course_builder import build_generated_courses

        courses = {c["slug"]: c for c in build_generated_courses()}
        first = courses["case-workshop"]["lessons"][0]
        questions = first["blocks"][-1]["questions"]
        assert len(questions) >= 4
        # answers are declined forms, not lemmas
        assert any(q["answer"].endswith(("а", "у", "е", "ой", "ы", "и"))
                   for q in questions)

    def test_dictation_lessons_carry_speak_field(self):
        from app.seed.course_builder import build_generated_courses

        courses = {c["slug"]: c for c in build_generated_courses()}
        lesson = courses["listening-path"]["lessons"][0]
        for q in lesson["blocks"][-1]["questions"]:
            assert q["speak"]  # frontend TTS source
