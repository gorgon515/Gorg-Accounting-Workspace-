"""Phase 15.75 Part 2 — Language Academy backend tests.

Covers curriculum, lesson generation + catalog scale, vocabulary expansion +
SM-2 SRS, grammar mistake detection, conversation flow, listening grading,
pronunciation scoring, placement + assessment weakness detection, and the
deterministic daily coach. Follows the monkeypatch-`_DB` + reset-`_instance`
fixture pattern.
"""
import pytest

import language_academy.lessons
import language_academy.vocabulary
import language_academy.conversation
import language_academy.assessment
import language_academy.coach
import language_academy.grammar
import language_academy.listening
import language_academy.pronunciation
import language_academy.engine

ALL_LANGS = ["russian", "spanish", "french", "german", "italian", "japanese", "mandarin"]


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setattr(language_academy.lessons, "_DB", tmp_path / "lessons.db")
    monkeypatch.setattr(language_academy.vocabulary, "_DB", tmp_path / "vocab.db")
    monkeypatch.setattr(language_academy.conversation, "_DB", tmp_path / "conv.db")
    monkeypatch.setattr(language_academy.assessment, "_DB", tmp_path / "assess.db")
    monkeypatch.setattr(language_academy.coach, "_DB", tmp_path / "coach.db")
    mods = [language_academy.lessons, language_academy.vocabulary,
            language_academy.conversation, language_academy.assessment,
            language_academy.coach, language_academy.grammar,
            language_academy.listening, language_academy.pronunciation,
            language_academy.engine]
    for m in mods:
        if hasattr(m, "_instance"):
            m._instance = None
    yield
    for m in mods:
        if hasattr(m, "_instance"):
            m._instance = None


# ── Curriculum ───────────────────────────────────────────────────────────────
class TestCurriculum:
    def test_six_levels_each_language(self):
        from language_academy.curriculum import Curriculum
        c = Curriculum()
        for lang in ALL_LANGS:
            cur = c.for_language(lang)
            assert len(cur["levels"]) == 6
            assert [l["level"] for l in cur["levels"]] == ["A1", "A2", "B1", "B2", "C1", "C2"]

    def test_level_has_can_do_statements(self):
        from language_academy.curriculum import Curriculum
        lvl = Curriculum().level("spanish", "B1")
        assert lvl["can_do_statements"]
        assert lvl["target_word_count"] > 0
        assert "grammar_focus" in lvl and "topics" in lvl

    def test_unknown_language_raises(self):
        from language_academy.curriculum import Curriculum
        with pytest.raises(ValueError):
            Curriculum().for_language("klingon")

    def test_grammar_focus_includes_language_rules(self):
        from language_academy.curriculum import Curriculum
        lvl = Curriculum().level("german", "B1")
        ids = [g["id"] for g in lvl["grammar_focus"]]
        assert any(i.startswith("de_") for i in ids)


# ── Lessons ──────────────────────────────────────────────────────────────────
class TestLessons:
    def test_generate_has_all_sections(self):
        from language_academy.lessons import get_lesson_engine
        lesson = get_lesson_engine().generate("spanish", "A2", "food")
        for key in ("id", "title", "language", "level", "topic", "objectives",
                    "vocabulary", "grammar", "reading", "listening_script",
                    "conversation_practice", "exercises", "assessment"):
            assert key in lesson, f"missing {key}"
        assert lesson["vocabulary"]
        assert lesson["grammar"]["title"]
        assert "passage" in lesson["reading"] and "glossary" in lesson["reading"]
        assert isinstance(lesson["listening_script"], str) and lesson["listening_script"]
        assert "scenario" in lesson["conversation_practice"]
        assert lesson["exercises"]
        assert lesson["assessment"]["questions"]

    def test_vocabulary_carries_translation(self):
        from language_academy.lessons import get_lesson_engine
        lesson = get_lesson_engine().generate("french", "A2", "food")
        assert all("translation" in w for w in lesson["vocabulary"])
        assert any(w["translation"] for w in lesson["vocabulary"])

    def test_exercise_types_present(self):
        from language_academy.lessons import get_lesson_engine
        lesson = get_lesson_engine().generate("german", "A2", "food")
        types = {e["type"] for e in lesson["exercises"]}
        assert "translation" in types
        assert "matching" in types or "fill_in_blank" in types

    def test_deterministic_id(self):
        from language_academy.lessons import get_lesson_engine, lesson_id
        e = get_lesson_engine()
        l1 = e.generate("italian", "B1", "business")
        assert l1["id"] == lesson_id("italian", "B1", "business")
        l2 = e.generate("italian", "B1", "business")
        assert l1["id"] == l2["id"]

    def test_catalog_exceeds_hundreds(self):
        from language_academy.lessons import get_lesson_engine
        e = get_lesson_engine()
        all_lessons = e.list(limit=10000)
        assert len(all_lessons) > 100
        # 7 langs x 6 levels x 12 topics
        assert e.count() == 7 * 6 * 12

    def test_list_filtered(self):
        from language_academy.lessons import get_lesson_engine
        e = get_lesson_engine()
        sp = e.list(language="spanish", limit=10000)
        assert all(l["language"] == "spanish" for l in sp)
        assert len(sp) == 6 * 12

    def test_get_generates_when_absent(self):
        from language_academy.lessons import get_lesson_engine, lesson_id
        e = get_lesson_engine()
        lid = lesson_id("japanese", "A1", "greetings")
        lesson = e.get(lid)
        assert lesson is not None
        assert lesson["id"] == lid

    def test_invalid_topic_raises(self):
        from language_academy.lessons import get_lesson_engine
        with pytest.raises(ValueError):
            get_lesson_engine().generate("spanish", "A1", "nonsense")


# ── Vocabulary + SRS ─────────────────────────────────────────────────────────
class TestVocabulary:
    def test_expansion_yields_entries_per_language(self):
        from language_academy.vocabulary import get_vocabulary_system
        v = get_vocabulary_system()
        stats = v.stats()
        assert stats["total_entries"] > 100
        for lang in ALL_LANGS:
            assert stats["by_language"].get(lang, 0) > 0

    def test_list_by_topic(self):
        from language_academy.vocabulary import get_vocabulary_system
        v = get_vocabulary_system()
        rows = v.list("spanish", topic="food")
        assert rows
        assert all(r["topic"] == "food" for r in rows)
        assert all(r["language"] == "spanish" for r in rows)

    def test_topic_counts(self):
        from language_academy.vocabulary import get_vocabulary_system
        v = get_vocabulary_system()
        topics = v.topics("french")
        assert topics
        assert all(t["count"] > 0 for t in topics)
        ids = {t["topic"] for t in topics}
        assert "accounting" in ids and "investing" in ids

    def test_search(self):
        from language_academy.vocabulary import get_vocabulary_system
        v = get_vocabulary_system()
        res = v.search("spanish", "money")
        assert any("money" in r["headword"].lower() or "money" in r["definition"].lower() for r in res)

    def test_review_returns_cards(self):
        from language_academy.vocabulary import get_vocabulary_system
        v = get_vocabulary_system()
        cards = v.review("spanish", limit=10)
        assert cards
        assert all("card_id" in c for c in cards)
        assert all("headword" in c for c in cards)

    def test_grade_sm2_updates_interval_and_ease(self):
        from language_academy.vocabulary import get_vocabulary_system
        v = get_vocabulary_system()
        cards = v.review("german", limit=5)
        cid = cards[0]["card_id"]
        r1 = v.grade(cid, 5)
        assert r1["reps"] == 1
        assert r1["interval"] == 1
        r2 = v.grade(cid, 5)
        assert r2["reps"] == 2
        assert r2["interval"] == 6
        r3 = v.grade(cid, 5)
        assert r3["reps"] == 3
        assert r3["interval"] > 6  # interval * ease
        assert r3["ease"] >= 2.5

    def test_grade_fail_resets(self):
        from language_academy.vocabulary import get_vocabulary_system
        v = get_vocabulary_system()
        cards = v.review("italian", limit=5)
        cid = cards[0]["card_id"]
        v.grade(cid, 5)
        v.grade(cid, 5)
        r = v.grade(cid, 1)  # fail
        assert r["reps"] == 0
        assert r["interval"] == 1
        assert r["ease"] >= 1.3  # ease never below floor

    def test_grade_ease_floor(self):
        from language_academy.vocabulary import get_vocabulary_system
        v = get_vocabulary_system()
        cards = v.review("spanish", limit=5)
        cid = cards[0]["card_id"]
        for _ in range(8):
            r = v.grade(cid, 0)
        assert r["ease"] >= 1.3

    def test_grade_unknown_card_raises(self):
        from language_academy.vocabulary import get_vocabulary_system
        with pytest.raises(KeyError):
            get_vocabulary_system().grade("does_not_exist", 4)


# ── Grammar ──────────────────────────────────────────────────────────────────
class TestGrammar:
    def test_lessons_filtered_by_language(self):
        from language_academy.grammar import get_grammar_academy
        g = get_grammar_academy()
        rules = g.lessons("spanish")
        langs = {r["language"] for r in rules}
        assert langs <= {"spanish", "generic"}
        assert any(r["language"] == "spanish" for r in rules)

    def test_lessons_by_tier(self):
        from language_academy.grammar import get_grammar_academy
        g = get_grammar_academy()
        beginner = g.lessons("french", "beginner")
        assert all(r["level"] in ("A1", "A2") for r in beginner)

    def test_check_catches_wrong_sentence(self):
        from language_academy.grammar import get_grammar_academy
        g = get_grammar_academy()
        # 'soy cansado' is a known Spanish ser/estar mistake.
        res = g.check("spanish", "Hoy soy cansado y triste.")
        assert res["found"], "should detect the ser/estar mistake"
        assert any(f["right"] == "estoy cansado" for f in res["found"])
        assert res["score"] < 100
        assert res["clean"] is False

    def test_check_clean_sentence(self):
        from language_academy.grammar import get_grammar_academy
        g = get_grammar_academy()
        res = g.check("spanish", "Me gusta el café por la mañana.")
        assert res["clean"] is True
        assert res["score"] == 100

    def test_check_generic_subject_verb(self):
        from language_academy.grammar import get_grammar_academy
        g = get_grammar_academy()
        res = g.check("japanese", "he work very hard every day.")
        assert any("works" in f["right"] for f in res["found"])

    def test_get_rule(self):
        from language_academy.grammar import get_grammar_academy
        g = get_grammar_academy()
        rule = g.get("de_cases")
        assert rule and rule["id"] == "de_cases"
        assert g.get("nope") is None


# ── Conversation ─────────────────────────────────────────────────────────────
class TestConversation:
    def test_scenarios_present(self):
        from language_academy.conversation import get_conversation_simulator
        s = get_conversation_simulator()
        ids = {sc["id"] for sc in s.scenarios()}
        for need in ("restaurant", "airport", "job_interview", "tax_consultation",
                     "investment_pitch"):
            assert need in ids

    def test_start_returns_opening(self):
        from language_academy.conversation import get_conversation_simulator
        s = get_conversation_simulator()
        out = s.start("spanish", "restaurant", "A2")
        assert out["session_id"]
        assert out["opening_line"]
        assert out["target_vocab"]

    def test_respond_advances_with_feedback(self):
        from language_academy.conversation import get_conversation_simulator
        s = get_conversation_simulator()
        out = s.start("french", "hotel", "A2")
        r1 = s.respond(out["session_id"], "Yes, I have a reservation under Smith.")
        assert r1["turn"] == 1
        assert "feedback" in r1
        assert "score" in r1["feedback"]
        assert "corrections" in r1
        r2 = s.respond(out["session_id"], "My name is John Smith.")
        assert r2["turn"] == 2
        # AI line should change as the scenario advances
        assert r1["ai_response"] != r2["ai_response"] or r2["complete"]

    def test_respond_corrections_use_grammar(self):
        from language_academy.conversation import get_conversation_simulator
        s = get_conversation_simulator()
        out = s.start("spanish", "restaurant", "A2")
        r = s.respond(out["session_id"], "Hoy soy cansado pero quiero comer.")
        assert r["corrections"]["found"]  # grammar.check caught the mistake

    def test_history(self):
        from language_academy.conversation import get_conversation_simulator
        s = get_conversation_simulator()
        out = s.start("italian", "shopping", "A2")
        s.respond(out["session_id"], "I need a medium size, please.")
        h = s.history(out["session_id"])
        speakers = [t["speaker"] for t in h["turns"]]
        assert "ai" in speakers and "user" in speakers

    def test_unknown_session_raises(self):
        from language_academy.conversation import get_conversation_simulator
        with pytest.raises(KeyError):
            get_conversation_simulator().respond("nope", "hi")


# ── Listening ────────────────────────────────────────────────────────────────
class TestListening:
    def test_list_and_filter(self):
        from language_academy.listening import get_listening_academy
        la = get_listening_academy()
        all_ex = la.list(language="spanish")
        assert len(all_ex) >= 15
        a1 = la.list(level="A1")
        assert all(e["level"] == "A1" for e in a1)

    def test_get_hides_answers(self):
        from language_academy.listening import get_listening_academy
        la = get_listening_academy()
        ex = la.get("lis_a1_intro", language="spanish")
        assert ex and "transcript" in ex
        assert all("answer" not in q for q in ex["questions"])

    def test_grade_all_correct(self):
        from language_academy.listening import get_listening_academy
        la = get_listening_academy()
        res = la.grade("lis_a1_intro", ["Maria", "Spain", "two"])
        assert res["score"] == 1.0
        assert res["passed"] is True

    def test_grade_partial(self):
        from language_academy.listening import get_listening_academy
        la = get_listening_academy()
        res = la.grade("lis_a1_intro", ["Maria", "Italy", "three"])
        assert res["correct"] == 1
        assert 0.0 < res["score"] < 1.0

    def test_grade_unknown_raises(self):
        from language_academy.listening import get_listening_academy
        with pytest.raises(KeyError):
            get_listening_academy().grade("nope", [])


# ── Pronunciation ────────────────────────────────────────────────────────────
class TestPronunciation:
    def test_identical_is_perfect(self):
        from language_academy.pronunciation import get_pronunciation_lab
        p = get_pronunciation_lab()
        res = p.score("spanish", "Hola, buenos días.", "Hola, buenos días.")
        assert res["accuracy"] == 100.0
        assert res["overall"] >= 99.0
        assert res["corrections"] == []

    def test_different_is_lower(self):
        from language_academy.pronunciation import get_pronunciation_lab
        p = get_pronunciation_lab()
        res = p.score("spanish", "Hola buenos días", "Adios noches frias")
        assert res["overall"] < 70
        assert res["corrections"]
        assert res["drills"]

    def test_partial_match_mid_range(self):
        from language_academy.pronunciation import get_pronunciation_lab
        p = get_pronunciation_lab()
        res = p.score("french", "je voudrais un café", "je voudrais un thé")
        assert 50 < res["overall"] < 100
        assert any(c["expected"] == "café" for c in res["corrections"])

    def test_all_metrics_in_range(self):
        from language_academy.pronunciation import get_pronunciation_lab
        p = get_pronunciation_lab()
        res = p.score("german", "Guten Morgen", "Guten Abend")
        for k in ("accuracy", "fluency", "clarity", "intonation", "overall"):
            assert 0 <= res[k] <= 100


# ── Assessment ───────────────────────────────────────────────────────────────
class TestAssessment:
    def test_placement_returns_test(self):
        from language_academy.assessment import get_assessment_system
        a = get_assessment_system()
        test = a.placement("spanish")
        assert test["questions"]
        assert all("answer" not in q for q in test["questions"])

    def test_placement_grade_estimates_cefr(self):
        from language_academy.assessment import get_assessment_system, _test_id
        a = get_assessment_system()
        a.placement("spanish")
        # Answer everything correctly using the stored (graded) version.
        graded = a._load_test(_test_id("spanish", "placement", "v1"))
        answers = [q["answer"] for q in graded["questions"]]
        res = a.placement_grade("spanish", answers)
        assert res["estimated_level"] in ["A1", "A2", "B1", "B2", "C1", "C2"]
        assert res["estimated_level"] == "C2"  # all correct → top level
        assert res["per_level"]
        assert res["per_area"]

    def test_placement_grade_low_score(self):
        from language_academy.assessment import get_assessment_system
        a = get_assessment_system()
        a.placement("russian")
        res = a.placement_grade("russian", ["wrong"] * 30)
        assert res["estimated_level"] == "A1"
        assert res["score"] == 0.0

    def test_tests_generated(self):
        from language_academy.assessment import get_assessment_system
        a = get_assessment_system()
        tests = a.tests(language="spanish")
        assert tests
        kinds = {t["kind"] for t in tests}
        assert "unit" in kinds and "level" in kinds

    def test_get_test_hides_answers(self):
        from language_academy.assessment import get_assessment_system
        a = get_assessment_system()
        tests = a.tests(language="french", level="A2", kind="unit")
        body = a.get_test(tests[0]["id"])
        assert body
        assert all("answer" not in q for q in body["questions"])

    def test_submit_returns_weaknesses_and_recommendations(self):
        from language_academy.assessment import get_assessment_system
        a = get_assessment_system()
        tests = a.tests(language="spanish", level="A2", kind="unit")
        tid = tests[0]["id"]
        # Submit all-wrong answers → weaknesses + recommendations.
        body = a._load_test(tid)
        n = len(body["questions"])
        res = a.submit(tid, ["___wrong___"] * n)
        assert res["score"] == 0.0
        assert res["passed"] is False
        assert res["weaknesses"]
        assert res["recommendations"]

    def test_submit_all_correct_passes(self):
        from language_academy.assessment import get_assessment_system
        a = get_assessment_system()
        tests = a.tests(language="german", level="A2", kind="unit")
        tid = tests[0]["id"]
        body = a._load_test(tid)
        answers = [q["answer"] for q in body["questions"]]
        res = a.submit(tid, answers)
        assert res["score"] == 1.0
        assert res["passed"] is True
        assert res["weaknesses"] == []

    def test_submit_unknown_raises(self):
        from language_academy.assessment import get_assessment_system
        with pytest.raises(KeyError):
            get_assessment_system().submit("tst_unknown_id", [])


# ── Coach ────────────────────────────────────────────────────────────────────
class TestCoach:
    def test_today_has_all_sections(self):
        from language_academy.coach import get_daily_coach
        c = get_daily_coach()
        plan = c.today("spanish")
        for key in ("date", "language", "lesson", "vocabulary", "review",
                    "conversation", "listening", "assessment"):
            assert key in plan, f"missing {key}"
        assert plan["lesson"]["id"]
        assert plan["vocabulary"]
        assert plan["conversation"]["scenario"]
        assert plan["listening"]["id"]
        assert plan["assessment"]["questions"]

    def test_today_is_stable_across_calls(self):
        from language_academy.coach import get_daily_coach
        c = get_daily_coach()
        p1 = c.today("french")
        p2 = c.today("french")
        assert p1["lesson"]["id"] == p2["lesson"]["id"]
        assert p1["conversation"]["scenario"] == p2["conversation"]["scenario"]
        assert p1["listening"]["id"] == p2["listening"]["id"]
        assert [v["word"] for v in p1["vocabulary"]] == [v["word"] for v in p2["vocabulary"]]

    def test_today_differs_by_language(self):
        from language_academy.coach import get_daily_coach
        c = get_daily_coach()
        es = c.today("spanish")
        de = c.today("german")
        assert es["language"] != de["language"]

    def test_unknown_language_raises(self):
        from language_academy.coach import get_daily_coach
        with pytest.raises(ValueError):
            get_daily_coach().today("klingon")


# ── Facade / engine ──────────────────────────────────────────────────────────
class TestEngine:
    def test_singleton_and_stats(self):
        from language_academy.engine import get_language_academy
        a = get_language_academy()
        assert a is get_language_academy()
        s = a.stats()
        assert s["languages"] == 7
        assert s["levels"] == 6
        assert s["vocabulary"]["total_entries"] > 100
        assert s["lessons"]["catalog_size"] == 7 * 6 * 12

    def test_passthrough_curriculum(self):
        from language_academy.engine import get_language_academy
        a = get_language_academy()
        cur = a.get_curriculum("italian")
        assert len(cur["levels"]) == 6
        one = a.get_curriculum("italian", "B1")
        assert one["level"] == "B1"

    def test_passthrough_placement_grade(self):
        from language_academy.engine import get_language_academy
        a = get_language_academy()
        test = a.placement("spanish")
        assert "questions" in test
        graded = a.placement("spanish", ["x"] * len(test["questions"]))
        assert "estimated_level" in graded

    def test_auto_vocab_expansion_on_init(self):
        from language_academy.engine import get_language_academy
        a = get_language_academy()
        rows = a.list_vocabulary("spanish", topic="accounting")
        assert rows
