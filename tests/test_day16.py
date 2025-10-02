# tests/test_day16.py
import datetime as dt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Ensure models are registered with Base
import swimsmart.models as _models  # noqa: F401

from swimsmart.api.main import create_app
from swimsmart.api import deps as api_deps
from swimsmart.api.authz import get_current_user
from swimsmart.models import User, UserRole, TrainingSession
from swimsmart.auth import hash_password


# -----------------------
# Test client & helpers
# -----------------------
@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """
    Build a FastAPI TestClient wired to the function-scoped db_session.
    """
    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            # pytest fixture handles closing/disposing
            pass

    app.dependency_overrides[api_deps.get_db] = _override_get_db
    return TestClient(app)


def _get_db_from_client(client: TestClient) -> Session:
    """
    Pull the same DB session the app uses in tests.
    """
    gen = client.app.dependency_overrides[api_deps.get_db]()
    return next(gen)


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


# -----------------------
# Day 16 “Coach overview”
# -----------------------
def test_coach_overview_and_leaderboard(client: TestClient):
    """
    Day 16 goal: verify a coach can see multi-swimmer information useful for an
    overview/leaderboard experience, using only the coach routes that exist.

    Steps:
      1) Create a coach and two swimmers.
      2) As the coach, create sessions for each swimmer and add sets.
      3) Fetch each swimmer’s dashboard rows and aggregate total distances.
      4) Build a simple leaderboard (in the test) and assert ordering.
    """
    db = _get_db_from_client(client)

    # Create users
    coach = _ensure_user(db, "coach@example.com", UserRole.coach)
    s1 = _ensure_user(db, "lane1@example.com", UserRole.swimmer)
    s2 = _ensure_user(db, "lane2@example.com", UserRole.swimmer)

    # Act as coach for all calls below
    client.app.dependency_overrides[get_current_user] = lambda: coach

    # Sanity: coach can list swimmers
    r_list = client.get("/coach/swimmers")
    assert r_list.status_code == 200
    swimmers = r_list.json()
    emails = [row["email"] for row in swimmers]
    assert "lane1@example.com" in emails
    assert "lane2@example.com" in emails

    # -----------------------
    # Seed sessions & sets
    # -----------------------
    # Swimmer 1: 2 sessions with decent volume
    create_payloads_s1 = [
        {"date": "2025-08-01", "notes": "endurance"},
        {"date": "2025-08-02", "notes": "threshold"},
    ]
    s1_session_ids: list[int] = []
    for p in create_payloads_s1:
        r_create = client.post(f"/coach/swimmers/{s1.id}/sessions", json=p)
        assert r_create.status_code in (200, 201)
        s1_session_ids.append(r_create.json()["id"])

    # Add sets to swimmer 1’s sessions
    # S1 Session A: 100 x 4 (400m) + 50 x 4 (200m) => 600m
    r_add_a1 = client.post(
        f"/coach/swimmers/{s1.id}/sessions/{s1_session_ids[0]}/sets",
        json={
            "distance_m": 100,
            "reps": 4,
            "interval_sec": 90,
            "stroke": "free",
            "rpe": [6, 6, 6, 6],
            "rep_times_sec": [75, 76, 77, 78],
        },
    )
    assert r_add_a1.status_code == 200
    r_add_a2 = client.post(
        f"/coach/swimmers/{s1.id}/sessions/{s1_session_ids[0]}/sets",
        json={
            "distance_m": 50,
            "reps": 4,
            "interval_sec": 60,
            "stroke": "fly",
            "rpe": [7, 7, 7, 7],
            "rep_times_sec": [40, 41, 41, 40],
        },
    )
    assert r_add_a2.status_code == 200

    # S1 Session B: 200 x 3 (600m)
    r_add_b1 = client.post(
        f"/coach/swimmers/{s1.id}/sessions/{s1_session_ids[1]}/sets",
        json={
            "distance_m": 200,
            "reps": 3,
            "interval_sec": 180,
            "stroke": "free",
            "rpe": [7, 7, 7],
            "rep_times_sec": [150, 151, 149],
        },
    )
    assert r_add_b1.status_code == 200

    # Swimmer 2: 1 session with lower volume
    r_create_s2 = client.post(
        f"/coach/swimmers/{s2.id}/sessions",
        json={"date": "2025-08-01", "notes": "technique"},
    )
    assert r_create_s2.status_code in (200, 201)
    s2_session_id = r_create_s2.json()["id"]

    # S2: 100 x 3 (300m)
    r_add_s2 = client.post(
        f"/coach/swimmers/{s2.id}/sessions/{s2_session_id}/sets",
        json={
            "distance_m": 100,
            "reps": 3,
            "interval_sec": 100,
            "stroke": "back",
            "rpe": [5, 5, 5],
            "rep_times_sec": [80, 81, 82],
        },
    )
    assert r_add_s2.status_code == 200

    # -----------------------
    # Coach overview via per-swimmer dashboards (existing API)
    # -----------------------
    def total_for_swimmer(swimmer_id: int) -> float:
        # Use existing coach route: dashboard style, already summarized
        r = client.get(f"/coach/swimmers/{swimmer_id}/sessions?pace_per_m=100")
        assert r.status_code == 200
        rows = r.json()
        total = 0.0
        for row in rows:
            # every row has "total_distance_m"
            total += float(row.get("total_distance_m", 0.0))
        return total

    s1_total = total_for_swimmer(s1.id)  # expected: 600 + 600 = 1200
    s2_total = total_for_swimmer(s2.id)  # expected: 300

    assert s1_total == 1200.0
    assert s2_total == 300.0

    # “Leaderboard” built in the test (highest total distance first)
    leaderboard = sorted(
        [
            {"swimmer_id": s1.id, "email": "lane1@example.com", "total_distance_m": s1_total},
            {"swimmer_id": s2.id, "email": "lane2@example.com", "total_distance_m": s2_total},
        ],
        key=lambda x: x["total_distance_m"],
        reverse=True,
    )

    assert leaderboard[0]["email"] == "lane1@example.com"
    assert leaderboard[0]["total_distance_m"] == 1200.0
    assert leaderboard[1]["email"] == "lane2@example.com"
    assert leaderboard[1]["total_distance_m"] == 300.0

    # Clean up the override to avoid leaking auth state into other tests
    client.app.dependency_overrides.pop(get_current_user, None)
