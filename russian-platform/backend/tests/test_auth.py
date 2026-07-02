def test_register_and_me(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "anna@example.com", "password": "supersecret",
              "display_name": "Anna"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "anna@example.com"
    assert body["cefr_estimate"] == "A0"
    assert body["level"] == 1


def test_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "password": "supersecret",
               "display_name": "Dup"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "correcthorse",
              "display_name": "Bob"},
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "bob@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "eve@example.com", "password": "correcthorse",
              "display_name": "Eve"},
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "eve@example.com", "password": "correcthorse"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/vocabulary").status_code == 401


def test_short_password_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.com", "password": "short", "display_name": "X"},
    )
    assert response.status_code == 422
