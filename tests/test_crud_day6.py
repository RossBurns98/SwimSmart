import datetime as dt
from swimsmart import crud
from swimsmart.schemas import SetCreate


def _seed_sample_session(db, date):
    ts = crud.create_session(date, notes="seed", db=db)
    # free: 100x4, 303s
    crud.add_set(ts.id, SetCreate(
        distance_m=100, reps=4, interval_sec=90, stroke="free",
        rpe=[5,6,6,5], rep_times_sec=[75,76,77,75],
    ), db=db)
    # fly: 50x6, 244s
    crud.add_set(ts.id, SetCreate(
        distance_m=50, reps=6, interval_sec=60, stroke="fly",
        rpe=[7,7,8,7,7,7], rep_times_sec=[40,41,42,40,41,40],
    ), db=db)
    return ts.id


def test_get_session_analytics(db_session):
    sid = _seed_sample_session(db_session, dt.date(2025, 1, 1))
    data = crud.get_session_analytics(sid, pace_per_m=100, db=db_session)

    # detail
    assert data["detail"]["id"] == sid
    assert data["detail"]["totals"]["total_distance_m"] == 700.0

    # summary
    summary = data["summary"]
    assert summary["total_distance_m"] == 700.0
    assert summary["avg_rpe"] == 6.5
    assert summary["avg_pace_sec_per"] == 78.14
    assert summary["avg_pace_formatted"] == "1:18.14"

    # by_stroke
    bd = data["by_stroke"]
    assert bd["free"]["total_distance_m"] == 400.0
    assert bd["free"]["avg_pace_sec_per"] == 75.75
    assert bd["fly"]["total_distance_m"] == 300.0
    assert bd["fly"]["avg_pace_sec_per"] == 81.33

    # best_set
    best = data["best_set"]
    assert best is not None
    assert "pace_sec_per" in best and "pace_formatted" in best


def test_summarise_sessions(db_session):
    _seed_sample_session(db_session, dt.date(2025, 1, 1))
    _seed_sample_session(db_session, dt.date(2025, 1, 2))

    result = crud.summarise_sessions(dt.date(2025, 1, 1), dt.date(2025, 1, 2), pace_per_m=100, db=db_session)
    assert result["sessions"] == 2
    assert result["total_distance_m"] == 1400.0  # 700 + 700
    assert result["avg_rpe"] == 6.5              # same distribution
    # total time doubles: 547*2 = 1094 over 1400 -> (1094/1400)*100
    assert result["avg_pace_sec_per"] == round((1094/1400)*100, 2)
    assert result["avg_pace_formatted"] is not None


def test_list_sessions_with_summaries(db_session):
    a = _seed_sample_session(db_session, dt.date(2025, 1, 1))
    b = _seed_sample_session(db_session, dt.date(2025, 1, 2))
    rows = crud.list_sessions_with_summaries(limit=10, pace_per_m=100, db=db_session)
    assert len(rows) >= 2
    # rows are ordered desc by date; check structure and fields
    for row in rows:
        assert {"id","date","notes","total_distance_m","avg_rpe","avg_pace_sec_per","pace_basis_m","avg_pace_formatted"} <= set(row.keys())
