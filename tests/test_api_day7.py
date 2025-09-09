# tests/test_api_day7.py
import datetime as dt
from fastapi.testclient import TestClient

from swimsmart.api.main import create_app
from swimsmart.api.deps import get_db  # <-- import the dependency to override
from swimsmart import crud
from swimsmart.schemas import SetCreate

def test_get_session_detail_and_analytics(db_session):
    # seed via the fixture-backed session
    ts = crud.create_session(dt.date(2025, 1, 1), notes="AM", db=db_session)
    crud.add_set(ts.id, SetCreate(
        distance_m=100, reps=4, interval_sec=90, stroke="free",
        rpe=[5,6,6,5], rep_times_sec=[75,76,77,75],
    ), db=db_session)

    app = create_app()

    # override FastAPI's DB dependency to use our test session
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass  # pytest will handle closing

    app.dependency_overrides[get_db] = _override_get_db

    client = TestClient(app)

    # detail
    r = client.get(f"/sessions/{ts.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == ts.id
    assert body["totals"]["total_distance_m"] == 400.0

    # analytics
    r = client.get(f"/sessions/{ts.id}/analytics?pace_per_m=100")
    assert r.status_code == 200
    data = r.json()
    assert "detail" in data and "summary" in data and "by_stroke" in data
    assert data["summary"]["total_distance_m"] == 400.0
