# tests/test_api_day8.py
import datetime as dt
from fastapi.testclient import TestClient
from swimsmart.api.main import create_app
from swimsmart.api.deps import get_db
from swimsmart.api.authz import get_current_user
from swimsmart.models import User, UserRole
from swimsmart import crud
from swimsmart.schemas import SetCreate

def _make_client_with_db(db_session):
    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)

def _ensure_user(db, email: str, role: UserRole) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, password_hash="x", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def _auth_as(client: TestClient, db, email: str, role: UserRole) -> User:
    user = _ensure_user(db, email, role)
    client.app.dependency_overrides[get_current_user] = lambda: user
    return user

def _seed(db, date):
    sid = crud.create_session(date, notes=f"seed {date.isoformat()}", db=db).id
    # free: 100 x 4 -> 400m @ 303s
    crud.add_set(sid, SetCreate(
        distance_m=100, reps=4, interval_sec=90, stroke="free",
        rpe=[5,6,6,5], rep_times_sec=[75,76,77,75],
    ), db=db)
    # fly: 50 x 6 -> 300m @ 244s
    crud.add_set(sid, SetCreate(
        distance_m=50, reps=6, interval_sec=60, stroke="fly",
        rpe=[7,7,8,7,7,7], rep_times_sec=[40,41,42,40,41,40],
    ), db=db)
    return sid

def test_list_sessions_dashboard(db_session):
    _seed(db_session, dt.date(2025, 1, 1))
    _seed(db_session, dt.date(2025, 1, 2))

    client = _make_client_with_db(db_session)
    # Any authenticated role is fine for listing
    _auth_as(client, db_session, email="viewer@example.com", role=UserRole.swimmer)

    r = client.get("/sessions?limit=10&pace_per_m=100")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) >= 2

    # check row shape
    row = rows[0]
    for key in ["id", "date", "notes", "total_distance_m", "avg_rpe", "avg_pace_sec_per", "pace_basis_m", "avg_pace_formatted"]:
        assert key in row

def test_summarise_sessions_range(db_session):
    _seed(db_session, dt.date(2025, 1, 1))
    _seed(db_session, dt.date(2025, 1, 2))

    client = _make_client_with_db(db_session)
    _auth_as(client, db_session, email="viewer2@example.com", role=UserRole.swimmer)

    r = client.get("/sessions/range/summary?start=2025-01-01&end=2025-01-02&pace_per_m=100")
    assert r.status_code == 200
    data = r.json()
    assert data["sessions"] == 2
    assert data["total_distance_m"] == 1400.0
    assert data["avg_rpe"] == 6.5
    assert data["avg_pace_sec_per"] == 78.14
    assert data["avg_pace_formatted"] == "1:18.14"

def test_list_sessions_in_range_with_summary(db_session):
    _seed(db_session, dt.date(2025, 1, 1))
    _seed(db_session, dt.date(2025, 1, 2))

    client = _make_client_with_db(db_session)
    _auth_as(client, db_session, email="viewer3@example.com", role=UserRole.swimmer)

    r = client.get("/sessions/range?start=2025-01-01&end=2025-01-02&pace_per_m=100")
    assert r.status_code == 200
    payload = r.json()

    assert "sessions" in payload and "summary" in payload
    assert len(payload["sessions"]) == 2
    # check summary matches expectations
    s = payload["summary"]
    assert s["sessions"] == 2
    assert s["total_distance_m"] == 1400.0
    assert s["avg_pace_formatted"] == "1:18.14"

def test_bad_range_returns_400(db_session):
    client = _make_client_with_db(db_session)
    _auth_as(client, db_session, email="viewer4@example.com", role=UserRole.swimmer)

    r = client.get("/sessions/range/summary?start=2025-01-02&end=2025-01-01")
    assert r.status_code == 400
    assert r.json()["detail"] == "end must be >= start"
