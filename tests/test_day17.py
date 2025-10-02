# tests/test_day17.py
import datetime as dt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Ensure models loaded
import swimsmart.models as _models  # noqa: F401

from swimsmart.api.main import create_app
from swimsmart.api import deps as api_deps
from swimsmart.api.authz import get_current_user
from swimsmart.models import User, UserRole
from swimsmart.auth import hash_password


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[api_deps.get_db] = _override_get_db
    return TestClient(app)


def _get_db_from_client(client: TestClient) -> Session:
    gen = client.app.dependency_overrides[api_deps.get_db]()
    return next(gen)


def _ensure_user(db: Session, email: str, role: UserRole) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, password_hash=hash_password("irrelevant"), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.role != role:
            user.role = role
            db.commit()
            db.refresh(user)
    return user


def test_auth_header_errors_and_basic_422(client: TestClient):
    # No auth header
    r = client.get("/sessions")
    assert r.status_code == 401
    assert r.json()["detail"] == "Missing Authorization Header."

    # Wrong scheme
    r2 = client.get("/sessions", headers={"Authorization": "Token ABC"})
    assert r2.status_code == 401
    assert r2.json()["detail"] == "Authorization scheme must be Bearer."

    # Valid auth -> create a user, override current user
    db = _get_db_from_client(client)
    swimmer = _ensure_user(db, "teststroke@example.com", UserRole.swimmer)
    client.app.dependency_overrides[get_current_user] = lambda: swimmer

    # 422: bad stroke
    payload = {
        "date": "2025-09-01",
        "notes": "bad stroke test"
    }
    r_create = client.post("/sessions", json=payload)
    assert r_create.status_code in (200, 201)
    sid = r_create.json()["id"]

    # add set with invalid stroke
    bad_set = {
        "distance_m": 100,
        "reps": 2,
        "interval_sec": 90,
        "stroke": "freestyle",  # invalid
        "rpe": [5, 6],
        "rep_times_sec": [75, 76],
    }
    r_add = client.post(f"/sessions/{sid}/sets", json=bad_set)
    assert r_add.status_code == 422
    body = r_add.json()
    # our handler: {"detail": "...", "errors": [...]}
    assert "errors" in body

    # 422: reps/list mismatch
    mismatch_set = {
        "distance_m": 50,
        "reps": 3,
        "interval_sec": 60,
        "stroke": "free",
        "rpe": [5, 5],                # only 2
        "rep_times_sec": [40, 41, 42] # 3
    }
    r_add2 = client.post(f"/sessions/{sid}/sets", json=mismatch_set)
    assert r_add2.status_code == 422
    assert "errors" in r_add2.json()

    client.app.dependency_overrides.pop(get_current_user, None)


def test_404_and_400_paths(client: TestClient):
    # Auth with any user
    db = _get_db_from_client(client)
    swimmer = _ensure_user(db, "range@example.com", UserRole.swimmer)
    client.app.dependency_overrides[get_current_user] = lambda: swimmer

    # 404: non-existent session detail
    r_404 = client.get("/sessions/9999999")
    assert r_404.status_code == 404

    # 400: end < start in range summary
    r_400 = client.get("/sessions/range/summary?start=2025-01-02&end=2025-01-01")
    assert r_400.status_code == 400
    assert r_400.json()["detail"] == "end must be >= start"

    client.app.dependency_overrides.pop(get_current_user, None)
