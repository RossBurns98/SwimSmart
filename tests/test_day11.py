# tests/test_day11.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Ensure models are registered on Base before tables are created in conftest
import swimsmart.models as _models  # noqa: F401

from swimsmart.api.main import create_app
from swimsmart.api import deps as api_deps


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """
    Build a TestClient using the app factory and override get_db
    to use the sqlite session from conftest.py (function-scoped).
    """
    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[api_deps.get_db] = _override_get_db
    return TestClient(app)


def _assert_jwt_like(token: str) -> None:
    # Basic structure check: header.payload.signature (two dots)
    assert isinstance(token, str)
    assert token.count(".") == 2
    # Non-empty segments
    h, p, s = token.split(".")
    assert h and p and s


def test_signup_swimmer_then_login(client: TestClient):
    # signup
    r = client.post(
        "/auth/signup",
        json={"email": "alice@example.com", "password": "pw123456", "role": "swimmer"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "swimmer"

    # login
    r2 = client.post("/auth/login", json={"email": "alice@example.com", "password": "pw123456"})
    assert r2.status_code == 200
    data = r2.json()
    assert data["token_type"] == "bearer"
    _assert_jwt_like(data["access_token"])
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["role"] == "swimmer"


def test_signup_coach_then_login(client: TestClient):
    r = client.post(
        "/auth/signup",
        json={"email": "coach@example.com", "password": "coachpw", "role": "coach"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "coach"

    r2 = client.post("/auth/login", json={"email": "coach@example.com", "password": "coachpw"})
    assert r2.status_code == 200
    data = r2.json()
    assert data["token_type"] == "bearer"
    _assert_jwt_like(data["access_token"])
    assert data["user"]["role"] == "coach"


def test_duplicate_email_rejected(client: TestClient):
    # First signup ok
    r1 = client.post("/auth/signup", json={"email": "dup@example.com", "password": "pw", "role": "swimmer"})
    assert r1.status_code == 200

    # Second signup same email -> 409
    r2 = client.post("/auth/signup", json={"email": "dup@example.com", "password": "pw", "role": "coach"})
    assert r2.status_code == 409
    assert "email" in r2.json()["detail"].lower()


def test_login_bad_password_401(client: TestClient):
    # Create a user
    r = client.post("/auth/signup", json={"email": "badpw@example.com", "password": "rightpw", "role": "swimmer"})
    assert r.status_code == 200

    # Wrong password -> 401
    r2 = client.post("/auth/login", json={"email": "badpw@example.com", "password": "wrongpw"})
    assert r2.status_code == 401
    assert "invalid" in r2.json()["detail"].lower()
