from __future__ import annotations # for forward references

import datetime as dt
from typing import Optional # for notes

from sqlalchemy import select # queries
from sqlalchemy.orm import Session, selectinload #queries

from .db import SessionLocal # Session management
from .models import TrainingSession, Set # ORM models
from .schemas import SetCreate # for validation before inserting (pydantic)

# creating function and args, * here just means db must be passed as a keyword, returns TrainingSession
def create_session(session_date: dt.date, notes: Optional[str] = None, *, db: Optional[Session] = None,) -> TrainingSession:
    owns_session = db is None
    db = db or SessionLocal() # either makes a db or uses passed one
    try:
        ts = TrainingSession(date=session_date, notes=notes)
        db.add(ts) # puts in session
        db.commit() # writes row and finalises
        db.refresh(ts) # refreshes
        return ts
    finally: # runs through try block then closes owns_session, note someone elses.
        if owns_session:
            db.close()

def add_set(session_id: int, data: SetCreate, *, db: Optional[Session] = None) -> Set:
    owns_session = db is None
    db = db or SessionLocal()
    try: # Checking if parent exists
        parent = db.get(TrainingSession, session_id)
        if parent is None:
            raise ValueError (f"TrainingSession id={session_id} does not exist")
        
        s = Set(
            session_id = parent.id,
            distance_m = data.distance_m,
            reps = data.reps,
            interval_sec = data.interval_sec,
            stroke = data.stroke,
            rpe = list(data.rpe), # passing lists here to make sure I get python lists back
            rep_times_sec = list(data.rep_times_sec),
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s
    finally:
        if owns_session:
            db.close()

# getting various stats for sessions
def session_stats(ts: TrainingSession) -> dict:
    sets = ts.sets or []
    total_sets = len(sets)
    total_distance_m = sum(s.distance_m*s.reps for s in sets)
    total_reps = sum(s.reps for s in sets)

    all_rpe = [x for s in sets for x in (s.rpe or [])]
    all_times = [x for s in sets for x in (s.rep_times_sec or [])]

    avg_rpe = round(sum(all_rpe) / len(all_rpe), 2) if all_rpe else None
    avg_rep_time_sec = round(sum(all_times) / len(all_times), 2) if all_times else None

    return {
        "total_sets": total_sets,
        "total_distance_m": float(total_distance_m),
        "total_reps": float(total_reps),
        "avg_rpe": avg_rpe,
        "avg_rep_time_sec": avg_rep_time_sec,
    }

def get_session_detail(session_id: int,*,db: Optional[Session] = None,) -> dict:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        query = (
            select(TrainingSession)
            .options(selectinload(TrainingSession.sets))
            .where(TrainingSession.id == session_id)
        )
        ts = db.execute(query).scalars().first()
        if ts is None:
            raise ValueError(f"TrainingSession id={session_id} not found")

        totals = session_stats(ts)
        sets_payload = [
            {
                "id": s.id,
                "distance_m": s.distance_m,
                "reps": s.reps,
                "interval_sec": s.interval_sec,
                "stroke": s.stroke,
                "rpe": list(s.rpe or []),
                "rep_times_sec": list(s.rep_times_sec or []),
            }
            for s in ts.sets
        ]

        return {
            "id": ts.id,
            "date": ts.date.isoformat(),
            "notes": ts.notes,
            "sets": sets_payload,
            "totals": totals,
        }
    finally:
        if owns_session:
            db.close()
    
def list_sessions_with_totals(limit: Optional[int] = None, *, db: Optional[Session] = None) -> list[dict]:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        query = (
            select(TrainingSession)
            .options(selectinload(TrainingSession.sets))
            .order_by(TrainingSession.date.desc(), TrainingSession.id.desc())
        )
        if limit:
            query = query.limit(limit)

        sessions = db.execute(query).scalars().all()
        result: list[dict] = []
        for ts in sessions:
            stats = session_stats(ts)
            result.append(
                {
                    "id": ts.id,
                    "date": ts.date.isoformat(),
                    "notes": ts.notes,
                    **stats,  # expands totals
                }
            )
        return result
    finally:
        if owns_session:
            db.close()