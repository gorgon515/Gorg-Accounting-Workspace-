def _get_courses(client, auth_headers):
    response = client.get("/api/v1/lessons/courses", headers=auth_headers)
    assert response.status_code == 200
    return response.json()


def _pass_lesson(client, auth_headers, slug):
    """Fetch a lesson's mastery test and answer it correctly (answer keys
    live in the seed data; we re-derive them from the DB via the seed
    module to simulate a perfect learner)."""
    from app.seed.courses import COURSES

    for course in COURSES:
        for lesson in course["lessons"]:
            if lesson["slug"] == slug:
                answers = {}
                for block in lesson["blocks"]:
                    if block["type"] in ("exercise", "mastery_test"):
                        for q in block["questions"]:
                            answers[q["id"]] = q["answer"]
                response = client.post(
                    f"/api/v1/lessons/{slug}/complete",
                    json={"answers": answers},
                    headers=auth_headers,
                )
                assert response.status_code == 200, response.text
                return response.json()
    raise AssertionError(f"lesson {slug} not found in seed")


def test_courses_listed_in_order_with_gating(client, auth_headers):
    courses = _get_courses(client, auth_headers)
    assert courses[0]["slug"] == "a0-foundations"
    assert courses[1]["slug"] == "a1-survival"
    a0 = courses[0]["lessons"]
    assert a0[0]["unlocked"] is True
    assert all(lesson["unlocked"] is False for lesson in a0[1:])
    # Second course entirely locked
    assert all(l["unlocked"] is False for l in courses[1]["lessons"])


def test_locked_lesson_rejects_access(client, auth_headers):
    response = client.get("/api/v1/lessons/a0-02-cyrillic-new", headers=auth_headers)
    assert response.status_code == 403


def test_lesson_answers_not_leaked(client, auth_headers):
    lesson = client.get("/api/v1/lessons/a0-01-cyrillic-friends",
                        headers=auth_headers).json()
    for block in lesson["blocks"]:
        if block["type"] in ("exercise", "mastery_test"):
            for q in block["questions"]:
                assert "answer" not in q


def test_passing_unlocks_next_and_grants_xp_and_cards(client, auth_headers):
    result = _pass_lesson(client, auth_headers, "a0-01-cyrillic-friends")
    assert result["passed"] is True
    assert result["score"] == 1.0

    courses = _get_courses(client, auth_headers)
    a0 = courses[0]["lessons"]
    assert a0[0]["passed"] is True
    assert a0[1]["unlocked"] is True
    assert a0[2]["unlocked"] is False

    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    assert me["xp"] >= 50
    assert me["streak_days"] == 1


def test_failing_mastery_test_does_not_unlock(client, auth_headers):
    response = client.post(
        "/api/v1/lessons/a0-01-cyrillic-friends/complete",
        json={"answers": {"m1": "wrong", "m2": "wrong", "m3": "wrong",
                          "q1": "wrong", "q2": "wrong", "q3": "wrong",
                          "q4": "wrong"}},
        headers=auth_headers,
    )
    body = response.json()
    assert body["passed"] is False
    courses = _get_courses(client, auth_headers)
    assert courses[0]["lessons"][1]["unlocked"] is False


def test_vocab_lesson_creates_srs_cards(client, auth_headers):
    for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new", "a0-03-stress"):
        _pass_lesson(client, auth_headers, slug)
    result = _pass_lesson(client, auth_headers, "a0-04-greetings")
    assert result["new_srs_cards"] == 8  # the greetings vocabulary

    queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
    assert queue["total_due"] == 8
    lemmas = {c["lexeme"]["lemma"] for c in queue["cards"]}
    assert "спасибо" in lemmas


def test_first_lesson_achievement_awarded(client, auth_headers):
    result = _pass_lesson(client, auth_headers, "a0-01-cyrillic-friends")
    slugs = [a["slug"] for a in result["achievements"]]
    assert "first-lesson" in slugs
