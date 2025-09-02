# tests/test_crud.py
import datetime as dt
import pytest

from swimsmart import crud
from swimsmart.schemas import SetCreate


def test_create_session_and_get_detail_with_stats(db_session):
    # create a session (Block 1)
    ts = crud.create_session(session_date=dt.date(2025, 1, 1), notes="AM swim", db=db_session)
    assert ts.id is not None

    # add two sets (Block 2)
    s1 = SetCreate(
        distance_m=100, reps=4, interval_sec=90, stroke="free",
        rpe=[5, 6, 6, 5], rep_times_sec=[75, 76, 77, 75],
    )
    s2 = SetCreate(
        distance_m=50, reps=6, interval_sec=60, stroke="fly",
        rpe=[7, 7, 8, 7, 7, 7], rep_times_sec=[40, 41, 42, 40, 41, 40],
    )
    crud.add_set(ts.id, s1, db=db_session)
    crud.add_set(ts.id, s2, db=db_session)

    # get detail (Block 3)
    detail = crud.get_session_detail(ts.id, db=db_session)
    assert detail["id"] == ts.id
    assert detail["date"] == "2025-01-01"
    assert len(detail["sets"]) == 2

    # check computed totals/averages (helper used by Block 3)
    totals = detail["totals"]
    # total distance = 4*100 + 6*50 = 700
    assert totals["total_distance_m"] == 700.0
    # total reps = 4 + 6 = 10
    assert totals["total_reps"] == 10.0
    # avg RPE = (5+6+6+5+7+7+8+7+7+7)/10 = 6.5
    assert totals["avg_rpe"] == 6.5
    # avg time = (75+76+77+75 + 40+41+42+40+41+40)/10 = 50.7
    assert totals["avg_rep_time_sec"] == 54.7


def test_list_sessions_with_totals_order_and_limit(db_session):
    # older session without sets
    s_old = crud.create_session(session_date=dt.date(2024, 12, 31), db=db_session)
    # newer session with one set
    s_new = crud.create_session(session_date=dt.date(2025, 1, 2), notes="PM", db=db_session)
    payload = SetCreate(
        distance_m=200, reps=3, interval_sec=180, stroke="back",
        rpe=[6, 6, 7], rep_times_sec=[150, 152, 151],
    )
    crud.add_set(s_new.id, payload, db=db_session)

    # list (Block 4)
    rows = crud.list_sessions_with_totals(db=db_session)
    # newest first
    assert rows[0]["id"] == s_new.id
    assert rows[0]["total_distance_m"] == 600.0
    assert rows[1]["id"] == s_old.id
    assert rows[1]["total_distance_m"] == 0.0

    # limit=1 only returns the newest
    top1 = crud.list_sessions_with_totals(limit=1, db=db_session)
    assert len(top1) == 1 and top1[0]["id"] == s_new.id


def test_add_set_invalid_session_raises(db_session):
    bogus_id = 999999
    payload = SetCreate(
        distance_m=50, reps=2, interval_sec=60, stroke="free",
        rpe=[5, 6], rep_times_sec=[45, 46],
    )
    with pytest.raises(ValueError):
        crud.add_set(bogus_id, payload, db=db_session)
