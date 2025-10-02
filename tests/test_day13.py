# tests/test_day13.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import swimsmart.models as _models  # ensure models register

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


def _get_db_from_client(client: TestClient) -> Session:
    gen = client.app.dependency_overrides[api_deps.get_db]()
    return next(gen)


def test_creator_swimmer_can_view_own_session_after_linking(client: TestClient):
    db = _get_db_from_client(client)
    swimmer = _ensure_user(db, "owner@example.com", UserRole.swimmer)
    coach = _ensure_user(db, "coach@example.com", UserRole.coach)

    # Create as swimmer (links user_id)
    client.app.dependency_overrides[get_current_user] = lambda: swimmer
    r_create = client.post("/sessions", json={"date": "2025-04-01", "notes": "endurance"})
    assert r_create.status_code in (200, 201)
    sid = r_create.json()["id"]

    # Owner swimmer can now view -> 200
    r_owner_view = client.get(f"/sessions/{sid}")
    assert r_owner_view.status_code == 200
    assert r_owner_view.json()["id"] == sid

    # Another swimmer cannot view -> 403
    other = _ensure_user(db, "other@example.com", UserRole.swimmer)
    client.app.dependency_overrides[get_current_user] = lambda: other
    r_other_view = client.get(f"/sessions/{sid}")
    assert r_other_view.status_code == 403

    # Coach can view -> 200
    client.app.dependency_overrides[get_current_user] = lambda: coach
    r_coach_view = client.get(f"/sessions/{sid}")
    assert r_coach_view.status_code == 200
    assert r_coach_view.json()["id"] == sid

    client.app.dependency_overrides.pop(get_current_user, None)


def test_owner_can_add_set_after_linking(client: TestClient):
    db = _get_db_from_client(client)
    swimmer = _ensure_user(db, "setowner@example.com", UserRole.swimmer)
    other = _ensure_user(db, "notowner@example.com", UserRole.swimmer)
    coach = _ensure_user(db, "coach2@example.com", UserRole.coach)

    # Create as swimmer → links to swimmer
    client.app.dependency_overrides[get_current_user] = lambda: swimmer
    r_create = client.post("/sessions", json={"date": "2025-04-02", "notes": "threshold"})
    assert r_create.status_code in (200, 201)
    sid = r_create.json()["id"]

    # Owner adds set → 200
    r_owner_add = client.post(
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
    assert r_owner_add.status_code == 200
    assert r_owner_add.json()["session_id"] == sid

    # Other swimmer tries -> 403
    client.app.dependency_overrides[get_current_user] = lambda: other
    r_other_add = client.post(
        f"/sessions/{sid}/sets",
        json={
            "distance_m": 50,
            "reps": 2,
            "interval_sec": 60,
            "stroke": "free",
            "rpe": [4, 5],
            "rep_times_sec": [45, 46],
        },
    )
    assert r_other_add.status_code == 403

    # Coach can add -> 200
    client.app.dependency_overrides[get_current_user] = lambda: coach
    r_coach_add = client.post(
        f"/sessions/{sid}/sets",
        json={
            "distance_m": 200,
            "reps": 2,
            "interval_sec": 180,
            "stroke": "free",
            "rpe": [7, 7],
            "rep_times_sec": [150, 151],
        },
    )
    assert r_coach_add.status_code == 200
    assert r_coach_add.json()["session_id"] == sid

    client.app.dependency_overrides.pop(get_current_user, None)
