from tests.test_lessons import _pass_lesson


def _enroll_cards(client, auth_headers):
    for slug in ("a0-01-cyrillic-friends", "a0-02-cyrillic-new",
                 "a0-03-stress", "a0-04-greetings"):
        _pass_lesson(client, auth_headers, slug)


def test_review_cycle_updates_memory_state(client, auth_headers):
    _enroll_cards(client, auth_headers)
    queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
    card = queue["cards"][0]
    assert card["state"] == "new"
    assert card["lexeme"]["stressed"]

    result = client.post(
        f"/api/v1/reviews/{card['card_id']}",
        json={"rating": 3},
        headers=auth_headers,
    ).json()
    assert result["state"] == "review"
    assert result["stability"] > 0
    assert result["interval_days"] > 1  # "good" on a new card => days, not minutes


def test_again_keeps_card_in_session(client, auth_headers):
    _enroll_cards(client, auth_headers)
    queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
    card_id = queue["cards"][0]["card_id"]
    result = client.post(
        f"/api/v1/reviews/{card_id}", json={"rating": 1}, headers=auth_headers
    ).json()
    assert result["state"] == "learning"
    assert result["interval_days"] < 0.05  # minutes, not days


def test_invalid_rating_rejected(client, auth_headers):
    _enroll_cards(client, auth_headers)
    queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
    card_id = queue["cards"][0]["card_id"]
    response = client.post(
        f"/api/v1/reviews/{card_id}", json={"rating": 9}, headers=auth_headers
    )
    assert response.status_code == 422


def test_cannot_review_others_cards(client, auth_headers):
    _enroll_cards(client, auth_headers)
    queue = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
    card_id = queue["cards"][0]["card_id"]

    other = client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "password123",
              "display_name": "Other"},
    ).json()
    response = client.post(
        f"/api/v1/reviews/{card_id}",
        json={"rating": 3},
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert response.status_code == 404


def test_reviewed_card_leaves_queue(client, auth_headers):
    _enroll_cards(client, auth_headers)
    before = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
    card_id = before["cards"][0]["card_id"]
    client.post(f"/api/v1/reviews/{card_id}", json={"rating": 4},
                headers=auth_headers)
    after = client.get("/api/v1/reviews/queue", headers=auth_headers).json()
    assert after["total_due"] == before["total_due"] - 1
    assert card_id not in [c["card_id"] for c in after["cards"]]
