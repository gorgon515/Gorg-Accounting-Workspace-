from app.services.speech import score_pronunciation, strip_stress
from tests.test_lessons import _pass_lesson


class TestPronunciationScoring:
    def test_perfect_match(self):
        result = score_pronunciation("Я живу́ в Москве́", "я живу в москве")
        assert result["overall_score"] == 100.0
        assert all(w["status"] == "correct" for w in result["words"])

    def test_stress_marks_ignored(self):
        assert strip_stress("говори́ть") == "говорить"

    def test_missed_word_detected(self):
        result = score_pronunciation("я хочу кофе", "я кофе")
        missed = [w for w in result["words"] if w["status"] == "missed"]
        assert [w["word"] for w in missed] == ["хочу"]
        assert result["overall_score"] < 100

    def test_close_word_partial_credit(self):
        result = score_pronunciation("один", "адин")
        assert result["words"][0]["status"] == "close"
        assert 0 < result["overall_score"] < 100

    def test_empty_target(self):
        assert score_pronunciation("", "что-то")["overall_score"] == 0.0


def test_pronunciation_endpoint_logs_attempt(client, auth_headers):
    result = client.post(
        "/api/v1/practice/pronunciation",
        json={"target_text": "Я хочу́ ко́фе", "recognized_text": "я хочу кофе"},
        headers=auth_headers,
    ).json()
    assert result["overall_score"] == 100.0


def test_quiz_targets_learner_vocabulary(client, auth_headers):
    for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                 "a0-03-stress", "a0-04-greetings"):
        _pass_lesson(client, auth_headers, slug)
    quiz = client.get("/api/v1/practice/quiz?size=5", headers=auth_headers).json()
    assert quiz["type"] == "vocabulary_quiz"
    assert len(quiz["questions"]) == 5
    for q in quiz["questions"]:
        assert q["answer"] in q["options"]
        assert len(set(q["options"])) == len(q["options"])


def test_story_requires_generative_provider(client, auth_headers):
    response = client.get("/api/v1/practice/story", headers=auth_headers)
    assert response.status_code == 409  # offline mode: clear guidance instead


def test_writing_submission_offline(client, auth_headers):
    result = client.post(
        "/api/v1/practice/writing",
        json={"prompt": "Опишите ваш день", "text": "Я живу в Москве. Я люблю кофе."},
        headers=auth_headers,
    ).json()
    assert result["word_count"] == 7
    assert result["feedback_available"] is False


def test_dashboard_aggregates(client, auth_headers):
    for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                 "a0-03-stress", "a0-04-greetings"):
        _pass_lesson(client, auth_headers, slug)
    queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
    client.post(f"/api/v1/reviews/{queue['cards'][0]['card_id']}",
                json={"rating": 3}, headers=auth_headers)

    dash = client.get("/api/v1/analytics/dashboard", headers=auth_headers).json()
    assert dash["cefr"]["level"] == "A0"
    assert dash["streak_days"] == 1
    assert dash["xp"]["level"] >= 2  # 4 lessons + achievements ≈ 300+ XP
    assert dash["vocabulary"]["card_states"]["review"] == 1
    assert dash["reviews_7d"]["total"] == 1
    assert dash["reviews_7d"]["accuracy"] == 1.0
    assert dash["activity"]["lesson_completed"] == 4
    assert any(a["slug"] == "first-lesson" for a in dash["achievements"])


def test_dashboard_empty_user(client, auth_headers):
    dash = client.get("/api/v1/analytics/dashboard", headers=auth_headers).json()
    assert dash["cefr"]["level"] == "A0"
    assert dash["vocabulary"]["known_words"] == 0
    assert dash["reviews_7d"]["accuracy"] is None
