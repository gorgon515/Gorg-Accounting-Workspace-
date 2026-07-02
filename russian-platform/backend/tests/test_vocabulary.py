def test_list_vocabulary(client, auth_headers):
    response = client.get("/api/v1/vocabulary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 90
    # Sorted by frequency: the most common words come first
    first = body["items"][0]
    assert first["frequency_rank"] is not None
    assert first["frequency_rank"] <= 5


def test_search_by_translation(client, auth_headers):
    response = client.get("/api/v1/vocabulary?q=water", headers=auth_headers)
    lemmas = [item["lemma"] for item in response.json()["items"]]
    assert "вода" in lemmas


def test_filter_by_pos(client, auth_headers):
    response = client.get("/api/v1/vocabulary?pos=verb", headers=auth_headers)
    items = response.json()["items"]
    assert items and all(i["part_of_speech"] == "verb" for i in items)


def test_lexeme_detail_has_full_payload(client, auth_headers):
    listing = client.get("/api/v1/vocabulary?q=говорить", headers=auth_headers).json()
    lexeme_id = listing["items"][0]["id"]
    detail = client.get(f"/api/v1/vocabulary/{lexeme_id}", headers=auth_headers).json()
    assert detail["stressed"] == "говори́ть"
    assert detail["ipa"].startswith("[")
    assert detail["aspect"] == "imperfective"
    assert detail["aspect_partner"] == "сказа́ть"
    assert detail["inflections"]["present"]["я"] == "говорю́"
    assert detail["examples"]
    assert detail["government"]


def test_alphabet_served_with_language(client, auth_headers):
    response = client.get("/api/v1/vocabulary/language/ru", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["name_native"] == "Русский"
    assert len(body["alphabet"]) == 33
    assert any(letter["letter"].startswith("Ы") for letter in body["alphabet"])
    assert body["pronunciation_rules"]
