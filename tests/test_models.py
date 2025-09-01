import datetime as dt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from swimsmart.db import Base
from swimsmart import models

def make_memory_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()

def test_insert_session_and_set_success():
    db = make_memory_session()

    s = models.TrainingSession(date=dt.date(2024, 9, 1), notes="Good day")
    db.add(s)
    db.flush()  # gives s.id

    st = models.Set(
        session_id=s.id,
        distance_m=100,
        reps=3,
        interval_sec=60,
        stroke="Free",
        rpe=[5, 6, 7],
        rep_times_sec=[65, 66, 67],
    )
    db.add(st)
    db.commit()

    loaded = db.get(models.TrainingSession, s.id)
    assert loaded is not None
    assert len(loaded.sets) == 1
    assert loaded.sets[0].rpe == [5, 6, 7]

    db.close()

def test_set_with_null_reps_raises_integrity_error():
    db = make_memory_session()

    s = models.TrainingSession(date=dt.date(2024, 9, 1), notes=None)
    db.add(s)
    db.flush()

    bad = models.Set(
        session_id=s.id,
        distance_m=100,
        reps=None,              # NOT NULL -> should fail on commit
        interval_sec=60,
        stroke="Free",
        rpe=[5, 6, 7],
        rep_times_sec=[65, 66, 67],
    )
    db.add(bad)

    with pytest.raises(IntegrityError):
        db.commit()

    db.close()
