import datetime as dt
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from swimsmart import crud
from swimsmart.schemas import SetCreate
from swimsmart.services import calculate_pace_per, format_seconds_mm_ss, session_summary
from swimsmart.models import TrainingSession


def test_calculate_pace_per_variants():
    # 400m in 300s
    assert calculate_pace_per(400, 300, 100) == 75.0
    assert calculate_pace_per(400, 300, 50) == 37.5
    assert calculate_pace_per(400, 300, 25) == 18.75

    # guards
    assert calculate_pace_per(0, 300, 100) is None
    assert calculate_pace_per(400, 0, 100) is None
    assert calculate_pace_per(400, 300, 0) is None


def test_format_seconds_mm_ss_basic_and_edge():
    # basic
    assert format_seconds_mm_ss(78.14) == "1:18.14"
    assert format_seconds_mm_ss(5.07) == "0:05.07"
    assert format_seconds_mm_ss(None) is None

    # edge: rounding overflow (e.g., 59.995 -> 1:00.00)
    assert format_seconds_mm_ss(59.995) == "1:00.00"
    # another minute rollover edge
    assert format_seconds_mm_ss(119.999) == "2:00.00"


def test_session_summary_with_pace_basis(db_session):
    # Build a real session with two sets:
    # Set1: 100m x 4 with times [75, 76, 77, 75]
    # Set2:  50m x 6 with times [40, 41, 42, 40, 41, 40]
    # Totals: distance = 700m; time = 547s; avg RPE = 6.5
    ts = crud.create_session(dt.date(2025, 1, 1), notes="AM", db=db_session)

    crud.add_set(ts.id, SetCreate(
        distance_m=100, reps=4, interval_sec=90, stroke="free",
        rpe=[5, 6, 6, 5], rep_times_sec=[75, 76, 77, 75],
    ), db=db_session)

    crud.add_set(ts.id, SetCreate(
        distance_m=50, reps=6, interval_sec=60, stroke="fly",
        rpe=[7, 7, 8, 7, 7, 7], rep_times_sec=[40, 41, 42, 40, 41, 40],
    ), db=db_session)

    # Load ORM object with sets eager-loaded
    q = (select(TrainingSession)
         .options(selectinload(TrainingSession.sets))
         .where(TrainingSession.id == ts.id))
    full_ts = db_session.execute(q).scalars().first()

    s100 = session_summary(full_ts, pace_per_m=100)
    s50  = session_summary(full_ts, pace_per_m=50)
    s25  = session_summary(full_ts, pace_per_m=25)

    # Totals stable
    assert s100["total_distance_m"] == 700.0
    assert s100["avg_rpe"] == 6.5

    # Pace correctness: (547 / 700) * per_m, rounded 2dp in summary
    assert s100["avg_pace_sec_per"] == round((547/700)*100, 2)  # 78.14
    assert s50["avg_pace_sec_per"]  == round((547/700)*50, 2)   # 39.07
    assert s25["avg_pace_sec_per"]  == round((547/700)*25, 2)   # 19.54

    # Human-friendly strings present
    assert s100["avg_pace_formatted"] == "1:18.14"
    assert s50["avg_pace_formatted"]  == "0:39.07"
    assert s25["avg_pace_formatted"]  == "0:19.54"
