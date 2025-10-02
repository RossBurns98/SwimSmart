# tests/test_day15.py
import datetime as dt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from swimsmart.api.main import create_app
from swimsmart.api.deps import get_db
from swimsmart.api.authz import get_current_user
from swimsmart.models import User, UserRole, TrainingSession


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    app = create_app()
    # share the pytest DB session with the app
    def _override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _ensure_user(db: Session, email: str, role: UserRole) -> User:
    # find by email first
    user = db.query(User).filter(User.email == email).first()
    if user is not None:
        return user
    # create if missing (simple hash to keep tests short)
    from swimsmart.auth import hash_password
    u = User(email=email, password_hash=hash_password("pw123456"), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _get_db_from_client(client: TestClient) -> Session:
    # grab the same session used by dependency override
    gen = client.app.dependency_overrides[get_db]()
    return next(iter(gen))


def test_swimmer_lists_own_sessions_and_cannot_see_others(client: TestClient):
    db = _get_db_from_client(client)
    alice = _ensure_user(db, "alice@example.com", UserRole.swimmer)
    bob = _ensure_user(db, "bob@example.com", UserRole.swimmer)

    # Act as Alice, create two sessions
    client.app.dependency_overrides[get_current_user] = lambda: alice
    r1 = client.post("/me/sessions", json={"date": "2025-06-01", "notes": "endurance"})
    assert r1.status_code in (200, 201)
    r2 = client.post("/me/sessions", json={"date": "2025-06-02", "notes": "speed"})
    assert r2.status_code in (200, 201)

    # Switch to Bob, create one session
    client.app.dependency_overrides[get_current_user] = lambda: bob
    r3 = client.post("/me/sessions", json={"date": "2025-06-03", "notes": "technique"})
    assert r3.status_code in (200, 201)

    # Bob lists his sessions -> should only see his 1
    r_list_bob = client.get("/me/sessions")
    assert r_list_bob.status_code == 200
    rows_bob = r_list_bob.json()
    # verify ownership by checking DB
    for row in rows_bob:
        ts = db.get(TrainingSession, row["id"])
        assert ts.user_id == bob.id

    # Bob tries to view Alice's session via /me -> 403
    alice_sid = r1.json()["id"]
    r_forbidden = client.get(f"/me/sessions/{alice_sid}")
    assert r_forbidden.status_code == 403


def test_swimmer_range_summary_and_add_set_guard(client: TestClient):
    db = _get_db_from_client(client)
    a = _ensure_user(db, "a@example.com", UserRole.swimmer)
    other = _ensure_user(db, "other@example.com", UserRole.swimmer)

    # Log a few sessions for A
    client.app.dependency_overrides[get_current_user] = lambda: a
    dates = ["2025-07-01", "2025-07-02"]
    ids: list[int] = []
    for d in dates:
        r = client.post("/me/sessions", json={"date": d, "notes": "work"})
        assert r.status_code in (200, 201)
        ids.append(r.json()["id"])

    # A adds a set to own session -> 200
    add_payload = {
        "distance_m": 100,
        "reps": 2,
        "interval_sec": 90,
        "stroke": "free",
        "rpe": [6, 6],
        "rep_times_sec": [75, 76],
    }
    r_add = client.post(f"/me/sessions/{ids[0]}/sets", json=add_payload)
    assert r_add.status_code in (200, 201)

    # Switch to other user, try adding set to A's session -> 403
    client.app.dependency_overrides[get_current_user] = lambda: other
    r_forbidden = client.post(f"/me/sessions/{ids[0]}/sets", json=add_payload)
    assert r_forbidden.status_code == 403

    # Back to A: range summary should include both
    client.app.dependency_overrides[get_current_user] = lambda: a
    r_sum = client.get("/me/sessions/range/summary", params={"start": "2025-07-01", "end": "2025-07-10"})
    assert r_sum.status_code == 200
    data = r_sum.json()
    assert data["sessions"] >= 2  # at least two sessions within range
