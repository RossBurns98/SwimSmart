# tests/test_day14.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import swimsmart.models as _models  # ensure models register

from swimsmart.api.main import create_app
from swimsmart.api import deps as api_deps
from swimsmart.api.authz import get_current_user
from swimsmart.models import User, UserRole, TrainingSession
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
    u = db.query(_models.User).filter(_models.User.email == email).first()
    if u is None:
        u = _models.User(email=email, password_hash=hash_password("pw"), role=role)
        db.add(u)
        db.commit()
        db.refresh(u)
    else:
        if u.role != role:
            u.role = role
            db.commit()
            db.refresh(u)
    return u


def _get_db_from_client(client: TestClient) -> Session:
    gen = client.app.dependency_overrides[api_deps.get_db]()
    return next(gen)


def test_swimmer_cannot_access_coach_endpoints(client: TestClient):
    db = _get_db_from_client(client)
    swimmer = _ensure_user(db, "s1@example.com", UserRole.swimmer)

    # act as swimmer
    client.app.dependency_overrides[get_current_user] = lambda: swimmer

    r1 = client.get("/coach/swimmers")
    assert r1.status_code == 403

    r2 = client.get("/coach/swimmers/999/sessions")
    assert r2.status_code == 403

    client.app.dependency_overrides.pop(get_current_user, None)


def test_coach_can_list_swimmers_and_manage_sessions(client: TestClient):
    db = _get_db_from_client(client)
    coach = _ensure_user(db, "coach@example.com", UserRole.coach)
    swimmer = _ensure_user(db, "swimmer@example.com", UserRole.swimmer)

    # act as coach
    client.app.dependency_overrides[get_current_user] = lambda: coach

    # list swimmers
    r_list = client.get("/coach/swimmers")
    assert r_list.status_code == 200
    swimmers = r_list.json()
    emails = [row["email"] for row in swimmers]
    assert "swimmer@example.com" in emails

    # create session for swimmer
    r_create = client.post(
        f"/coach/swimmers/{swimmer.id}/sessions",
        json={"date": "2025-05-01", "notes": "technique"},
    )
    assert r_create.status_code in (200, 201)
    sid = r_create.json()["id"]

    # verify owner is swimmer
    ts = db.get(TrainingSession, sid)
    assert ts is not None
    assert ts.user_id == swimmer.id

    # fetch session detail via coach route
    r_detail = client.get(f"/coach/swimmers/{swimmer.id}/sessions/{sid}")
    assert r_detail.status_code == 200
    assert r_detail.json()["id"] == sid

    # wrong swimmer id -> 409
    r_wrong = client.get(f"/coach/swimmers/{swimmer.id + 999}/sessions/{sid}")
    assert r_wrong.status_code == 409

    # add set via coach route
    r_add_set = client.post(
        f"/coach/swimmers/{swimmer.id}/sessions/{sid}/sets",
        json={
            "distance_m": 100,
            "reps": 2,
            "interval_sec": 90,
            "stroke": "free",
            "rpe": [5, 5],
            "rep_times_sec": [75, 76],
        },
    )
    assert r_add_set.status_code == 200
    assert r_add_set.json()["session_id"] == sid

    client.app.dependency_overrides.pop(get_current_user, None)
