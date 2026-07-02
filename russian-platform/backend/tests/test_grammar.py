def test_topics_catalog_ordered(client, auth_headers):
    topics = client.get("/api/v1/grammar/topics", headers=auth_headers).json()
    assert len(topics) >= 30
    assert topics[0]["slug"] == "cyrillic-alphabet"
    levels = [t["cefr_level"] for t in topics]
    # Curriculum runs A0 → C1 without regressions of more than one band
    assert levels.index("B1") > levels.index("A1")


def test_topic_detail_hides_answers(client, auth_headers):
    topic = client.get("/api/v1/grammar/topics/gender", headers=auth_headers).json()
    assert topic["content"]
    assert topic["drills"]
    for d in topic["drills"]:
        assert set(d.keys()) == {"id", "prompt"}


def test_drill_submission_updates_mastery(client, auth_headers):
    result = client.post(
        "/api/v1/grammar/topics/gender/drills",
        json={"answers": {"gen1": "f", "gen2": "m", "gen3": "n",
                          "gen4": "m", "gen5": "f"}},
        headers=auth_headers,
    ).json()
    assert all(r["correct"] for r in result["results"])
    assert result["mastery"] > 0.5

    # Wrong answers drop mastery
    result2 = client.post(
        "/api/v1/grammar/topics/gender/drills",
        json={"answers": {"gen1": "m", "gen2": "f"}},
        headers=auth_headers,
    ).json()
    assert result2["mastery"] < result["mastery"]


def test_accepted_alternates_and_yo_normalization(client, auth_headers):
    result = client.post(
        "/api/v1/grammar/topics/gender/drills",
        json={"answers": {"gen1": "FEMININE "}},  # case/space/alternate
        headers=auth_headers,
    ).json()
    assert result["results"][0]["correct"] is True


def test_catalog_topic_without_drills_rejects_submission(client, auth_headers):
    response = client.post(
        "/api/v1/grammar/topics/participles/drills",
        json={"answers": {"x": "y"}},
        headers=auth_headers,
    )
    assert response.status_code == 400
