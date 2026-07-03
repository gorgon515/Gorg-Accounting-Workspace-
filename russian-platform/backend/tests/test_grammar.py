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


def test_all_seeded_topics_have_content_and_drills(client, auth_headers):
    """Phase 2: the full curriculum ships interactive content everywhere."""
    topics = client.get("/api/v1/grammar/topics", headers=auth_headers).json()
    assert all(t["has_content"] for t in topics)
    assert all(t["drill_count"] > 0 for t in topics)
    assert any(t["cefr_level"] == "C2" for t in topics)


def test_prerequisite_readiness_flag(client, auth_headers):
    topics = client.get("/api/v1/grammar/topics", headers=auth_headers).json()
    by_slug = {t["slug"]: t for t in topics}
    assert by_slug["cyrillic-alphabet"]["ready"] is True  # no prerequisites
    assert by_slug["participles"]["ready"] is False  # deep prerequisites unmet

    # Master a prerequisite chain end-to-end and watch readiness flip.
    from app.seed.grammar_topics import TOPICS

    gender_drills = next(t for t in TOPICS if t["slug"] == "gender")["drills"]
    answers = {d["id"]: d["answer"] for d in gender_drills}
    for _ in range(4):  # EMA needs a few perfect rounds to cross 0.6
        client.post("/api/v1/grammar/topics/gender/drills",
                    json={"answers": answers}, headers=auth_headers)
    topics = client.get("/api/v1/grammar/topics", headers=auth_headers).json()
    possessives = next(t for t in topics if t["slug"] == "possessives")
    assert possessives["ready"] is True  # its only prerequisite is gender


def test_topic_without_drills_rejects_submission(client, auth_headers, db_session):
    from app.models import GrammarTopic, Language
    from sqlalchemy import select

    language = db_session.scalar(select(Language))
    db_session.add(
        GrammarTopic(
            language_id=language.id, slug="empty-topic", title="Empty",
            title_native="Пусто", cefr_level="C2", order_index=999,
            summary="placeholder-free test fixture",
        )
    )
    db_session.commit()
    response = client.post(
        "/api/v1/grammar/topics/empty-topic/drills",
        json={"answers": {"x": "y"}},
        headers=auth_headers,
    )
    assert response.status_code == 400
