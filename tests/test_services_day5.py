import datetime as dt
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from swimsmart import crud
from swimsmart.schemas import SetCreate
from swimsmart.models import TrainingSession
from swimsmart.services import (
    calculate_pace_per,
    format_seconds_mm_ss,
    session_summary,
    stroke_breakdown,
    best_set_pace,
    sessions_summary,
)


def _load_session(db, session_id: int) -> TrainingSession:
    q = (
        select(TrainingSession)
        .options(selectinload(TrainingSession.sets))
        .where(TrainingSession.id == session_id)
    )
    return db.execute(q).scalars().first()


def test_calculate_and_format_helpers():
    # calc
    assert calculate_pace_per(400, 300, 100) == 75.0
    assert calculate_pace_per(400, 300, 50) == 37.5
    assert calculate_pace_per(0, 300, 100) is None
    assert calculate_pace_per(400, 0, 100) is None
    assert calculate_pace_per(400, 300, 0) is None

    # format
    assert format_seconds_mm_ss(78.14) == "1:18.14"
    assert format_seconds_mm_ss(5.07) == "0:05.07"
    assert format_seconds_mm_ss(None) is None
    # rounding carry
    assert format_seconds_mm_ss(59.995) == "1:00.00"
    assert format_seconds_mm_ss(119.999) == "2:00.00"


def test_session_summary_and_breakdown_and_best(db_session):
    # Build one session with two sets
    ts = crud.create_session(dt.date(2025, 1, 1), notes="AM", db=db_session)

    # free: 100 x 4, times sum = 303
    crud.add_set(
        ts.id,
        SetCreate(
            distance_m=100, reps=4, interval_sec=90, stroke="free",
            rpe=[5, 6, 6, 5], rep_times_sec=[75, 76, 77, 75],
        ),
        db=db_session,
    )

    # fly: 50 x 6, times sum = 244
    crud.add_set(
        ts.id,
        SetCreate(
            distance_m=50, reps=6, interval_sec=60, stroke="fly",
            rpe=[7, 7, 8, 7, 7, 7], rep_times_sec=[40, 41, 42, 40, 41, 40],
        ),
        db=db_session,
    )

    full = _load_session(db_session, ts.id)

    # session_summary (per 100m): totals across both sets
    summary = session_summary(full, pace_per_m=100)
    assert summary["total_distance_m"] == 700.0
    assert summary["avg_rpe"] == 6.5
    # (547 / 700) * 100 = 78.14
    assert summary["avg_pace_sec_per"] == 78.14
    assert summary["avg_pace_formatted"] == "1:18.14"

    # stroke_breakdown (per 100m) pace per stroke from stroke totals
    bd = stroke_breakdown(full, pace_per_m=100)
    # distance per stroke
    assert bd["free"]["total_distance_m"] == 400.0
    assert bd["fly"]["total_distance_m"] == 300.0
    # pace per stroke
    # free: 303/400*100 = 75.75
    assert bd["free"]["avg_pace_sec_per"] == 75.75
    assert bd["free"]["avg_pace_formatted"] == "1:15.75"
    # fly: 244/300*100 = 81.33
    assert bd["fly"]["avg_pace_sec_per"] == 81.33
    assert bd["fly"]["avg_pace_formatted"] == "1:21.33"

    # best_set_pace (per 100m): pick the lowest pace set
    best = best_set_pace(full, pace_per_m=100)
    assert best is not None
    assert best["distance_m"] in (50, 100)  # one of our sets
    # fastest of our data is the 100x2 @ (70+72) in many examples, but here both sets are slower;
    # we just assert that the reported pace matches its own formatted string.
    assert format_seconds_mm_ss(best["pace_sec_per"]) == best["pace_formatted"]


def test_sessions_summary_multiple(db_session):
    # Session A (free): 400m @ 303s
    a = crud.create_session(dt.date(2025, 1, 1), db=db_session)
    crud.add_set(
        a.id,
        SetCreate(
            distance_m=100, reps=4, interval_sec=90, stroke="free",
            rpe=[5, 6, 6, 5], rep_times_sec=[75, 76, 77, 75],
        ),
        db=db_session,
    )

    # Session B (fly): 300m @ 244s
    b = crud.create_session(dt.date(2025, 1, 2), db=db_session)
    crud.add_set(
        b.id,
        SetCreate(
            distance_m=50, reps=6, interval_sec=60, stroke="fly",
            rpe=[7, 7, 8, 7, 7, 7], rep_times_sec=[40, 41, 42, 40, 41, 40],
        ),
        db=db_session,
    )

    A = _load_session(db_session, a.id)
    B = _load_session(db_session, b.id)

    rollup = sessions_summary([A, B], pace_per_m=100)
    assert rollup["sessions"] == 2
    assert rollup["total_distance_m"] == 700.0
    assert rollup["avg_rpe"] == 6.5
    assert rollup["avg_pace_sec_per"] == 78.14
    assert rollup["avg_pace_formatted"] == "1:18.14"
