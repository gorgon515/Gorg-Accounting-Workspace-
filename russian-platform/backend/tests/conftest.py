import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The app lifespan touches the env-configured engine (create_all + seed);
# give it a throwaway file DB. Test routes use the per-test in-memory
# session via dependency override.
_tmpdb = os.path.join(tempfile.mkdtemp(prefix="rli-test-"), "lifespan.db")
os.environ["RLP_DATABASE_URL"] = f"sqlite:///{_tmpdb}"
os.environ["RLP_SECRET_KEY"] = "test-secret-key-0123456789abcdef-32b"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.seed.runner import seed_all


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    seed_all(session)
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Lifespan (create_all + seed against the real engine) is skipped by
    # instantiating TestClient without a context manager entry for startup.
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "learner@example.com", "password": "password123",
              "display_name": "Learner"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
