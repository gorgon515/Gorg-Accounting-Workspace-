"""Phase 3 feature tests: exams, session reports, dictionary 2.0,
writing coach, error intelligence, pronunciation queue, curriculum v2."""


# --------------------------------------------------------------------- exams
class TestExams:
    def test_level_exam_has_sections_and_no_answer_keys(self, client, auth_headers):
        exam = client.get("/api/v1/exams/level/A1", headers=auth_headers).json()
        assert exam["time_limit_minutes"] == 20
        assert set(exam["sections"]) == {"vocabulary", "grammar", "reading", "listening"}
        for questions in exam["sections"].values():
            for q in questions:
                assert "_answer" not in q and "_accept" not in q
        assert all(q["options"] for q in exam["sections"]["vocabulary"])
        assert all(q["speak"] for q in exam["sections"]["listening"])

    def test_exam_is_deterministic_per_seed(self, client, auth_headers, db_session):
        from app.services.exams import build_level_exam

        first = build_level_exam(db_session, "A2", "fixed-seed")
        second = build_level_exam(db_session, "A2", "fixed-seed")
        assert first == second
        different = build_level_exam(db_session, "A2", "other-seed")
        assert first != different

    def test_perfect_submission_passes_and_lifts_cefr(self, client, auth_headers, db_session):
        from app.services.exams import build_level_exam

        exam = build_level_exam(db_session, "A1", "test-seed")
        answers = {q["id"]: q["_answer"]
                   for qs in exam["sections"].values() for q in qs}
        result = client.post(
            "/api/v1/exams/level/A1/submit",
            json={"seed": "test-seed", "answers": answers},
            headers=auth_headers,
        ).json()
        assert result["passed"] is True and result["score"] == 1.0
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        assert me["cefr_estimate"] == "A1"

        certificate = client.get(
            f"/api/v1/exams/certificates/{result['result_id']}",
            headers=auth_headers,
        ).json()
        assert certificate["level"] == "A1"
        assert certificate["certificate_id"].startswith("RLI-")

    def test_failed_exam_reports_weaknesses(self, client, auth_headers):
        exam = client.get("/api/v1/exams/level/A1", headers=auth_headers).json()
        answers = {q["id"]: "wrong"
                   for qs in exam["sections"].values() for q in qs}
        result = client.post(
            "/api/v1/exams/level/A1/submit",
            json={"seed": exam["seed"], "answers": answers},
            headers=auth_headers,
        ).json()
        assert result["passed"] is False
        assert result["worst_section"] in exam["sections"]
        assert result["weak_topics"]
        assert all(slug.startswith("grammar-")
                   for slug in result["recommended_lessons"])
        no_cert = client.get(
            f"/api/v1/exams/certificates/{result['result_id']}",
            headers=auth_headers,
        )
        assert no_cert.status_code == 409

    def test_placement_places_and_sets_estimate(self, client, auth_headers, db_session):
        from app.services.exams import build_placement_exam

        placement = client.get("/api/v1/exams/placement", headers=auth_headers).json()
        exam = build_placement_exam(db_session, placement["seed"])
        answers = {}
        for level in ("A1", "A2"):  # answer two bands perfectly, rest wrong
            for q in exam["bands"][level]:
                answers[f"{level}:{q['id']}"] = q["_answer"]
        result = client.post(
            "/api/v1/exams/placement/submit",
            json={"seed": placement["seed"], "answers": answers},
            headers=auth_headers,
        ).json()
        assert result["placed_level"] == "A2"
        me = client.get("/api/v1/auth/me", headers=auth_headers).json()
        assert me["cefr_estimate"] == "A2"

    def test_results_history(self, client, auth_headers):
        exam = client.get("/api/v1/exams/level/B1", headers=auth_headers).json()
        client.post("/api/v1/exams/level/B1/submit",
                    json={"seed": exam["seed"], "answers": {}},
                    headers=auth_headers)
        history = client.get("/api/v1/exams/results", headers=auth_headers).json()
        assert history and history[0]["kind"] == "level"


# ---------------------------------------------------------- session reports
class TestSessionReport:
    def test_report_metrics_and_transcript(self, client, auth_headers):
        start = client.post("/api/v1/conversation/sessions/cafe-order",
                            headers=auth_headers).json()
        sid = start["session_id"]
        for text in ("Я хочу кофе, пожалуйста", "С молоком, пожалуйста",
                     "Нет, спасибо", "Спасибо! Счёт, пожалуйста"):
            client.post(f"/api/v1/conversation/sessions/{sid}/messages",
                        json={"text": text}, headers=auth_headers)
        report = client.get(f"/api/v1/conversation/sessions/{sid}/report",
                            headers=auth_headers).json()
        assert report["completed"] is True
        assert report["metrics"]["user_turns"] == 4
        assert report["metrics"]["unique_words"] > 0
        assert 0 < report["metrics"]["vocabulary_diversity"] <= 1
        assert "кофе" in report["metrics"]["key_vocabulary_used"]
        assert len(report["transcript"]) == 9  # opening + 4 exchanges

    def test_new_scenarios_seeded_with_goals(self, client, auth_headers):
        scenarios = client.get("/api/v1/conversation/scenarios",
                               headers=auth_headers).json()
        slugs = {s["slug"] for s in scenarios}
        assert {"doctor-visit", "job-interview", "airport-checkin",
                "government-office", "first-date", "small-talk-weather",
                "shopping-clothes", "business-meeting"} <= slugs
        doctor = next(s for s in scenarios if s["slug"] == "doctor-visit")
        assert doctor["goals"] and doctor["grammar_focus"]

    def test_scripted_walkthrough_of_new_scenario(self, client, auth_headers):
        start = client.post("/api/v1/conversation/sessions/doctor-visit",
                            headers=auth_headers).json()
        sid = start["session_id"]
        reply = client.post(f"/api/v1/conversation/sessions/{sid}/messages",
                            json={"text": "У меня болит голова"},
                            headers=auth_headers).json()
        assert "давно" in reply["text"].lower()
        reply = client.post(f"/api/v1/conversation/sessions/{sid}/messages",
                            json={"text": "Два дня"}, headers=auth_headers).json()
        assert "реце́пт" in reply["text"].lower() or "лека́рство" in reply["text"].lower()


# ------------------------------------------------------------ dictionary 2.0
class TestDictionary2:
    def test_inflected_form_lookup(self, client, auth_headers):
        result = client.get("/api/v1/vocabulary?q=живу", headers=auth_headers).json()
        assert result["total"] == 0
        assert result["form_matches"]
        match = result["form_matches"][0]
        assert match["lemma"] == "жить"
        assert match["form_slot"] == "present.я"

    def test_declined_noun_lookup(self, client, auth_headers):
        result = client.get("/api/v1/vocabulary?q=книгу", headers=auth_headers).json()
        assert any(m["lemma"] == "книга" for m in result["form_matches"])

    def test_wildcard_search(self, client, auth_headers):
        result = client.get("/api/v1/vocabulary?q=*ость", headers=auth_headers).json()
        lemmas = {item["lemma"] for item in result["items"]}
        assert "возможность" in lemmas
        assert all(l.endswith("ость") for l in lemmas)

    def test_word_family(self, client, auth_headers):
        found = client.get("/api/v1/vocabulary?q=говорить", headers=auth_headers).json()
        lex_id = found["items"][0]["id"]
        family = client.get(f"/api/v1/vocabulary/{lex_id}/family",
                            headers=auth_headers).json()
        assert family["root"] == "говор"
        assert any(r["type"] == "synonym" or r["target"]
                   for r in family["relations"]) or family["same_root"] is not None


# ------------------------------------------------------------- writing coach
class TestWritingCoach:
    def test_analysis_detects_unknown_and_repetition(self, client, auth_headers):
        text = ("Москва большой город. Москва красивый город. "
                "Москва мой любимый город. Я люблю кнегу.")
        result = client.post("/api/v1/writing/analyze",
                             json={"kind": "journal", "text": text},
                             headers=auth_headers).json()
        assert result["word_count"] > 10
        unknown = {u["word"] for u in result["unknown_words"]}
        assert "кнегу" in unknown or any(
            u["suggestion"] == "книга" for u in result["unknown_words"])
        repeated = {r["lemma"] for r in result["repetition"]}
        assert "москва" in repeated  # repeated proper noun
        assert "город" in repeated  # repeated dictionary word
        assert result["srs_candidates"]
        assert result["llm_feedback_available"] is False

    def test_inflected_forms_count_as_known(self, client, auth_headers):
        result = client.post("/api/v1/writing/analyze",
                             json={"kind": "journal",
                                   "text": "Я читаю книгу и пью воду."},
                             headers=auth_headers).json()
        assert result["unknown_words"] == []
        assert result["dictionary_coverage"] == 1.0

    def test_history_tracks_recurring_mistakes(self, client, auth_headers):
        for _ in range(2):
            client.post("/api/v1/writing/analyze",
                        json={"kind": "journal", "text": "Я люблю кнегу."},
                        headers=auth_headers)
        history = client.get("/api/v1/writing/history", headers=auth_headers).json()
        assert len(history["submissions"]) == 2
        assert any(m["word"] == "кнегу" for m in history["recurring_mistakes"])

    def test_prompts_catalog(self, client, auth_headers):
        prompts = client.get("/api/v1/writing/prompts", headers=auth_headers).json()
        assert {p["kind"] for p in prompts} >= {"journal", "essay", "letter"}


# -------------------------------------------------------- error intelligence
class TestErrorIntelligence:
    def test_report_with_activity(self, client, auth_headers):
        from tests.test_lessons import _pass_lesson

        for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                     "a0-03-stress", "a0-04-greetings"):
            _pass_lesson(client, auth_headers, slug)
        queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
        client.post(f"/api/v1/reviews/{queue['cards'][0]['card_id']}",
                    json={"rating": 1}, headers=auth_headers)
        client.post(f"/api/v1/reviews/{queue['cards'][1]['card_id']}",
                    json={"rating": 3}, headers=auth_headers)

        report = client.get("/api/v1/analytics/report?period=week",
                            headers=auth_headers).json()
        assert report["reviews"]["total"] == 2
        assert report["reviews"]["lapses"] == 1
        assert report["forgotten_words"]
        assert report["recommendations"]

    def test_empty_report_recommends_progress(self, client, auth_headers):
        report = client.get("/api/v1/analytics/report?period=month",
                            headers=auth_headers).json()
        assert report["period"] == "month"
        assert report["recommendations"][0]["kind"] == "keep-going"


# --------------------------------------------------- pronunciation practice
class TestPronunciationQueue:
    def test_weak_targets_enter_queue_with_tips(self, client, auth_headers):
        client.post("/api/v1/practice/pronunciation",
                    json={"target_text": "Я хочу́ ры́бу",
                          "recognized_text": "я хочу это"},
                    headers=auth_headers)
        client.post("/api/v1/practice/pronunciation",
                    json={"target_text": "До́брый ве́чер",
                          "recognized_text": "добрый вечер"},
                    headers=auth_headers)
        queue = client.get("/api/v1/practice/pronunciation/queue",
                           headers=auth_headers).json()
        targets = [item["target_text"] for item in queue["queue"]]
        assert "Я хочу́ ры́бу" in targets  # weak
        assert "До́брый ве́чер" not in targets  # mastered
        weak = next(i for i in queue["queue"] if i["target_text"] == "Я хочу́ ры́бу")
        assert any("ы" in tip for tip in weak["tips"])


# ------------------------------------------------------------- curriculum v2
class TestCurriculumV2:
    def test_course_gating_by_prerequisite(self, client, auth_headers):
        courses = client.get("/api/v1/lessons/courses", headers=auth_headers).json()
        by_slug = {c["slug"]: c for c in courses}
        # No prerequisite → first lesson open.
        assert by_slug["a0-foundations"]["lessons"][0]["unlocked"] is True
        assert by_slug["phonetics-path"]["lessons"][0]["unlocked"] is True
        # Prerequisite unmet → locked.
        assert by_slug["a1-survival"]["lessons"][0]["unlocked"] is False
        assert by_slug["grammar-path"]["lessons"][0]["unlocked"] is False

    def test_prerequisite_course_unlocks_at_60_percent(self, client, auth_headers):
        from tests.test_lessons import _pass_lesson

        for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                     "a0-03-stress", "a0-04-greetings"):
            _pass_lesson(client, auth_headers, slug)  # 4/6 = 67%
        courses = client.get("/api/v1/lessons/courses", headers=auth_headers).json()
        by_slug = {c["slug"]: c for c in courses}
        assert by_slug["a1-survival"]["lessons"][0]["unlocked"] is True
        assert by_slug["grammar-path"]["lessons"][0]["unlocked"] is True
        # Sequential inside the unlocked course still applies.
        assert by_slug["a1-survival"]["lessons"][1]["unlocked"] is False
