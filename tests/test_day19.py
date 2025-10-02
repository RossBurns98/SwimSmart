# tests/test_day19.py
import datetime as dt
from fastapi.testclient import TestClient

from swimsmart.api.main import create_app
from swimsmart.api.deps import get_db
from swimsmart.api.authz import get_current_user
from swimsmart.models import User, UserRole, TrainingSession
from swimsmart.schemas import SetCreate
from swimsmart import crud
from swimsmart.auth import hash_password


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
    u = db.query(User).filter(User.email == email).first()
    if u is None:
        u = User(email=email, password_hash=hash_password("irrelevant"), role=role)
        db.add(u)
        db.commit()
        db.refresh(u)
    else:
        if u.role != role:
            u.role = role
            db.commit()
            db.refresh(u)
    return u


def test_export_single_session_owner_and_coach(db_session):
    client = _make_client_with_db(db_session)

    # create users
    swimmer = _ensure_user(db_session, "swim@example.com", UserRole.swimmer)
    coach = _ensure_user(db_session, "coach@example.com", UserRole.coach)

    # create a session owned by swimmer with a set
    ts = crud.create_session(dt.date(2025, 2, 1), notes="tempo", user_id=swimmer.id, db=db_session)
    crud.add_set(
        ts.id,
        SetCreate(distance_m=100, reps=4, interval_sec=90, stroke="free", rpe=[6,6,6,6], rep_times_sec=[75,76,75,76]),
        db=db_session,
    )

    # owner export -> 200 CSV
    client.app.dependency_overrides[get_current_user] = lambda: swimmer
    r_owner = client.get(f"/export/session/{ts.id}.csv")
    assert r_owner.status_code == 200
    assert r_owner.headers["content-type"].startswith("text/csv")
    body = r_owner.text
    assert "session_id,date,notes,owner_user_id,set_id,distance_m,reps,interval_sec,stroke,rpe,rep_times_sec" in body
    assert f"{ts.id}" in body

    # coach export -> 200 CSV
    client.app.dependency_overrides[get_current_user] = lambda: coach
    r_coach = client.get(f"/export/session/{ts.id}.csv")
    assert r_coach.status_code == 200
    assert "free" in r_coach.text

    client.app.dependency_overrides.pop(get_current_user, None)


def test_export_range_csv_swimmer_sees_only_own(db_session):
    client = _make_client_with_db(db_session)

    # two swimmers + coach
    a = _ensure_user(db_session, "a@example.com", UserRole.swimmer)
    b = _ensure_user(db_session, "b@example.com", UserRole.swimmer)
    coach = _ensure_user(db_session, "coach2@example.com", UserRole.coach)

    # sessions in range
    s1 = crud.create_session(dt.date(2025, 3, 1), notes="A-1", user_id=a.id, db=db_session)
    s2 = crud.create_session(dt.date(2025, 3, 2), notes="B-1", user_id=b.id, db=db_session)
    crud.add_set(s1.id, SetCreate(distance_m=50, reps=4, interval_sec=60, stroke="fly", rpe=[6,6,6,6], rep_times_sec=[40,41,40,41]), db=db_session)
    crud.add_set(s2.id, SetCreate(distance_m=100, reps=2, interval_sec=90, stroke="free", rpe=[5,6], rep_times_sec=[75,76]), db=db_session)

    # swimmer A export -> should include A but not B
    client.app.dependency_overrides[get_current_user] = lambda: a
    r_a = client.get("/export/range.csv?start=2025-03-01&end=2025-03-10")
    assert r_a.status_code == 200
    text_a = r_a.text
    assert "A-1" in text_a
    assert "B-1" not in text_a

    # coach export -> includes both
    client.app.dependency_overrides[get_current_user] = lambda: coach
    r_c = client.get("/export/range.csv?start=2025-03-01&end=2025-03-10")
    assert r_c.status_code == 200
    text_c = r_c.text
    assert "A-1" in text_c and "B-1" in text_c

    # coach filtered by swimmer_id -> only that swimmer
    r_c_filter = client.get(f"/export/range.csv?start=2025-03-01&end=2025-03-10&swimmer_id={a.id}")
    assert r_c_filter.status_code == 200
    text_cf = r_c_filter.text
    assert "A-1" in text_cf and "B-1" not in text_cf

    client.app.dependency_overrides.pop(get_current_user, None)


def test_export_range_bad_dates_400(db_session):
    client = _make_client_with_db(db_session)
    swimmer = _ensure_user(db_session, "x@example.com", UserRole.swimmer)
    client.app.dependency_overrides[get_current_user] = lambda: swimmer

    r = client.get("/export/range.csv?start=2025-04-10&end=2025-04-01")
    assert r.status_code == 400
    assert r.json()["detail"] == "end must be >= start"

    client.app.dependency_overrides.pop(get_current_user, None)
