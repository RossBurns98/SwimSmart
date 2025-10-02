# tests/test_day12.py
import datetime as dt
from swimsmart import crud
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Ensure models are registered with Base
import swimsmart.models as _models  # noqa: F401

from swimsmart.api.main import create_app
from swimsmart.api import deps as api_deps
from swimsmart.api.authz import get_current_user
from swimsmart.models import User, UserRole
from swimsmart.auth import hash_password


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """
    Create an app per test and wire it to the test DB session.
    We override get_db to yield the test session.
    """
    app = create_app()

    def _override_get_db():
        # yields the function-scoped session from conftest
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[api_deps.get_db] = _override_get_db
    return TestClient(app)


def _get_db_from_client(client: TestClient) -> Session:
    """
    Pull the same DB session the app uses in tests.
    This calls the override generator and takes its yielded value.
    """
    gen = client.app.dependency_overrides[api_deps.get_db]()
    db = next(gen)  # get the yielded session
    return db


def _ensure_user(db: Session, email: str, role: UserRole) -> User:
    """
    Idempotently create or fetch a user with the given role for tests.
    """
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


def test_auth_required_for_listing(client: TestClient):
    """
    /sessions requires authentication: unauthenticated -> 401
    authenticated (any role) -> 200
    """
    # No current user override => 401
    r = client.get("/sessions")
    assert r.status_code == 401

    # Override to act as an authenticated swimmer => 200
    db = _get_db_from_client(client)
    swimmer = _ensure_user(db, "u@example.com", UserRole.swimmer)

    def _as_swimmer():
        return swimmer

    client.app.dependency_overrides[get_current_user] = _as_swimmer

    r2 = client.get("/sessions")
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)

    # cleanup
    client.app.dependency_overrides.pop(get_current_user, None)



def test_coach_can_view_session_but_creator_cannot_until_day13_linking(client: TestClient):
    """
    Day 12 nuance:
    - TrainingSession.user_id is not linked on create(), so "owner" check fails
    - Swimmer trying to view => 403
    - Coach can view => 200
    """
    db = _get_db_from_client(client)
    swimmer = _ensure_user(db, "swim@example.com", UserRole.swimmer)
    coach = _ensure_user(db, "coach@example.com", UserRole.coach)

    # Create a session directly in the DB with NO owner link (user_id=None)
    sid = crud.create_session(
        session_date=dt.date(2025, 3, 1),
        notes="aerobic",
        user_id=None,
        db=db,
    ).id

    # Swimmer tries to view -> 403 (not owner)
    client.app.dependency_overrides[get_current_user] = lambda: swimmer
    r_swimmer_view = client.get(f"/sessions/{sid}")
    assert r_swimmer_view.status_code == 403

    # Coach can view -> 200
    client.app.dependency_overrides[get_current_user] = lambda: coach
    r_coach_view = client.get(f"/sessions/{sid}")
    assert r_coach_view.status_code == 200
    assert r_coach_view.json()["id"] == sid

    client.app.dependency_overrides.pop(get_current_user, None)

def test_add_set_requires_owner_or_coach(client: TestClient):
    db = _get_db_from_client(client)
    user_a = _ensure_user(db, "a@example.com", UserRole.swimmer)
    user_b = _ensure_user(db, "b@example.com", UserRole.swimmer)
    coach = _ensure_user(db, "coach2@example.com", UserRole.coach)

    # Create session as A
    client.app.dependency_overrides[get_current_user] = lambda: user_a
    r_create = client.post("/sessions", json={"date": "2025-03-02", "notes": "threshold"})
    assert r_create.status_code in (200, 201)
    sid = r_create.json()["id"]

    # B attempts to add a set -> 403
    client.app.dependency_overrides[get_current_user] = lambda: user_b
    r_b_add = client.post(
        f"/sessions/{sid}/sets",
        json={
            "distance_m": 100,
            "reps": 3,
            "interval_sec": 90,
            "stroke": "free",
            "rpe": [5, 6, 5],
            "rep_times_sec": [75, 76, 77],
        },
    )
    assert r_b_add.status_code == 403

    # Coach can add a set -> 200
    client.app.dependency_overrides[get_current_user] = lambda: coach
    r_coach_add = client.post(
        f"/sessions/{sid}/sets",
        json={
            "distance_m": 100,
            "reps": 2,
            "interval_sec": 90,
            "stroke": "free",
            "rpe": [6, 6],
            "rep_times_sec": [74, 75],
        },
    )
    assert r_coach_add.status_code == 200
    assert r_coach_add.json()["session_id"] == sid

    client.app.dependency_overrides.pop(get_current_user, None)
