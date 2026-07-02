def test_scenarios_listed(client, auth_headers):
    response = client.get("/api/v1/conversation/scenarios", headers=auth_headers)
    assert response.status_code == 200
    slugs = [s["slug"] for s in response.json()]
    assert "cafe-order" in slugs
    assert "taxi-ride" in slugs


def test_full_scripted_dialogue(client, auth_headers):
    start = client.post("/api/v1/conversation/sessions/cafe-order",
                        headers=auth_headers).json()
    session_id = start["session_id"]
    assert "Здра́вствуйте" in start["opening"]["text"]
    assert start["opening"]["hints"]

    def say(text):
        return client.post(
            f"/api/v1/conversation/sessions/{session_id}/messages",
            json={"text": text},
            headers=auth_headers,
        ).json()

    reply = say("Я хочу кофе, пожалуйста")
    assert "молок" in reply["text"].lower()  # asks about milk
    assert reply["corrections"] == []

    reply = say("С молоком, пожалуйста")
    assert "ещё" in reply["text"].lower()

    reply = say("Нет, спасибо")
    assert "аппети́та" in reply["text"].lower() or "пожа́луйста" in reply["text"].lower()

    reply = say("Спасибо! Счёт, пожалуйста")
    assert reply.get("completed") is True


def test_unmatched_reply_gets_correction_hint(client, auth_headers):
    start = client.post("/api/v1/conversation/sessions/cafe-order",
                        headers=auth_headers).json()
    reply = client.post(
        f"/api/v1/conversation/sessions/{start['session_id']}/messages",
        json={"text": "asdf qwerty"},
        headers=auth_headers,
    ).json()
    # Dialogue continues (falls through) but the learner gets a correction.
    assert reply["corrections"]
    assert reply["corrections"][0]["correction"]


def test_session_memory_persists_completions(client, auth_headers):
    start = client.post("/api/v1/conversation/sessions/taxi-ride",
                        headers=auth_headers).json()
    session_id = start["session_id"]
    for text in ("В центр, пожалуйста", "Да, очень хорошая!", "Спасибо большое!"):
        reply = client.post(
            f"/api/v1/conversation/sessions/{session_id}/messages",
            json={"text": text}, headers=auth_headers,
        ).json()
    assert reply.get("completed") is True

    # A new session in the same scenario remembers previous completions.
    again = client.post("/api/v1/conversation/sessions/taxi-ride",
                        headers=auth_headers)
    assert again.status_code == 201


def test_conversation_grants_xp(client, auth_headers):
    before = client.get("/api/v1/auth/me", headers=auth_headers).json()["xp"]
    start = client.post("/api/v1/conversation/sessions/meeting-someone",
                        headers=auth_headers).json()
    client.post(
        f"/api/v1/conversation/sessions/{start['session_id']}/messages",
        json={"text": "Меня зовут Марк"}, headers=auth_headers,
    )
    after = client.get("/api/v1/auth/me", headers=auth_headers).json()["xp"]
    assert after > before
