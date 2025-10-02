# tests/test_day18.py
import datetime as dt
from sqlalchemy.orm import Session

from swimsmart.db import Base
import swimsmart.models as _models  # ensure models are registered with Base
from swimsmart.seed import seed_dataset
from swimsmart.models import User, UserRole, TrainingSession
from swimsmart.schemas import SetCreate


def test_programmatic_seed_small(db_session: Session):
    """
    Seed into the test database (not the file DB) using the programmatic API.
    Verify counts and ownership are correct and data looks plausible.
    """
    # run with small numbers for speed/determinism
    summary = seed_dataset(
        swimmers=4,
        sessions_per_swimmer=6,
        min_sets_per_session=2,
        max_sets_per_session=3,
        coach_email="coach@example.com",
        start_date=dt.date(2025, 1, 1),
        days_span=10,
        rng_seed=42,
        reset=True,
        db=db_session # wipe rows in this test DB first
    )

    # basic summary assertions
    assert summary["swimmers"] == 4
    assert summary["sessions"] == 4 * 6
    assert summary["sets"] >= 4 * 6 * 2  # at least min sets

    # coach exists
    coach = db_session.query(User).filter(User.email == "coach@example.com").first()
    assert coach is not None and coach.role == UserRole.coach

    # all swimmers exist and have role swimmer
    swimmers = db_session.query(User).filter(User.role == UserRole.swimmer).all()
    assert len(swimmers) == 4

    # every swimmer has sessions, and sessions are owned correctly
    for sw in swimmers:
        sessions = db_session.query(TrainingSession).filter(TrainingSession.user_id == sw.id).all()
        # should have exactly 6 each
        assert len(sessions) == 6
        for ts in sessions:
            # owned correctly
            assert ts.user_id == sw.id
            # has 2..3 sets
            assert 2 <= len(ts.sets) <= 3
            # payload looks valid
            for s in ts.sets:
                assert s.reps == len(s.rpe) == len(s.rep_times_sec)
                assert s.distance_m > 0
                # reasonable interval / time ranges
                assert 10 <= s.interval_sec <= 3600
                for x in s.rep_times_sec:
                    assert 10 <= x <= 3600


def test_seed_idempotent_reset_true(db_session: Session):
    """
    If we run seed twice with reset=True, the final counts should match the second run
    (since we wipe the rows).
    """
    s1 = seed_dataset(swimmers=3, sessions_per_swimmer=2, reset=True, rng_seed=1,start_date=dt.date(2025, 1, 1), db=db_session)
    s2 = seed_dataset(swimmers=5, sessions_per_swimmer=1, reset=True, rng_seed=1,start_date=dt.date(2025, 1, 1), db=db_session)

    # second summary dictates final state
    assert s2["swimmers"] == 5
    assert s2["sessions"] == 5 * 1

    swimmers = db_session.query(User).filter(User.role == UserRole.swimmer).count()
    sessions = db_session.query(TrainingSession).count()
    assert swimmers == 5
    assert sessions == 5 * 1
