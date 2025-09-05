from __future__ import annotations # for forward references

import datetime as dt
from typing import Optional # for notes

from sqlalchemy import select # queries
from sqlalchemy.orm import Session, selectinload #queries

from .db import SessionLocal # Session management
from .models import TrainingSession, Set # ORM models
from .schemas import SetCreate # for validation before inserting (pydantic)
from . import services

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
    total_distance_m = 0
    for s in sets:
        total_distance_m += s.distance_m * s.reps
    total_reps = 0
    for s in sets:
        total_reps += s.reps

    all_rpe: list[float] = []
    for s in sets:
        rpes = s.rpe or []
        for x in rpes:
            all_rpe.append(x)
    
    all_times: list[float] = []
    for s in sets:
        times = s.rep_times_sec or []
        for x in times:
            all_times.append(x)

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
        sets_payload: list[dict] = []
        for s in ts.sets:    
            item = {
                "id": s.id,
                "distance_m": s.distance_m,
                "reps": s.reps,
                "interval_sec": s.interval_sec,
                "stroke": s.stroke,
                "rpe": list(s.rpe or []),
                "rep_times_sec": list(s.rep_times_sec or []),
            }
            sets_payload.append(item)

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

def fetch_session_with_sets(session_id: int, *, db: Optional[Session] = None) -> Optional[TrainingSession]:
    """
    Eager-loads one TrainingSession or returns None if not found.
    """
    owns = db is None
    db = db or SessionLocal()
    try:
        q = (
            select(TrainingSession)
            .options(selectinload(TrainingSession.sets))
            .where(TrainingSession.id == session_id)
        )
        return db.execute(q).scalars().first()
    finally:
        if owns:
            db.close()

def fetch_sessions_in_range(start_date: dt.date, end_date: dt.date, *, db: Optional[Session] = None) -> list[TrainingSession]:
    """
    Load all session in range start_date to end_date inclusive, sets are eager-loaded.
    """
    owns = db is None
    db = db or SessionLocal()
    try:
        q = (
            select(TrainingSession)
            .options(selectinload(TrainingSession.sets))
            .where(TrainingSession.date >= start_date)
            .where(TrainingSession.date <= end_date)
            .order_by(TrainingSession.date.asc(), TrainingSession.id.asc())
        )
        return db.execute(q).scalars().all()
    finally:
        if owns:
            db.close()

def get_session_analytics(session_id: int, pace_per_m: int = 100, *, db: Optional[Session] = None) -> dict:
    """
    Return analytics for one session:
    -'detail': the same dict as a get_session_detail
    -'summary': session_summary()
    -'by_stroke': stroke_breakdown{}
    -'best_set': best_set_pace()
    """
    owns = db is None
    db = db or SessionLocal()
    try:
        detail = get_session_detail(session_id, db=db)

        ts = fetch_session_with_sets(session_id, db=db)
        if ts is None:
            raise ValueError(f"Training session id={session_id} not found")
        
        summary = services.session_summary(ts, pace_per_m=pace_per_m)
        by_stroke = services.stroke_breakdown(ts, pace_per_m=pace_per_m)
        best = services.best_set_pace(ts, pace_per_m=pace_per_m)

        return {
            "detail": detail,
            "summary": summary,
            "by_stroke": by_stroke,
            "best_set": best
        }
    finally:
        if owns:
            db.close()

def summarise_sessions(start_date: dt.date, end_date: dt.date, pace_per_m: int = 100, *, db:Optional[Session] = None) -> dict:
    """
    Aggregate analytics across a date range
    """
    owns = db is None
    db = db or SessionLocal()
    try:
        sessions = fetch_sessions_in_range(start_date, end_date, db=db)
        return services.sessions_summary(sessions, pace_per_m=pace_per_m)
    finally:
        if owns:
            db.close()

def list_sessions_with_summaries(limit: Optional[int] = None, pace_per_m: int = 100, *, db: Optional[Session] = None) -> list[dict]:
    """
    Returns a compact list of session metrics ready to use in a dashboard.
    Only top level, session stats, doesn't include details per set.
    """
    owns = db is None
    db = db or SessionLocal()
    try: 
        q = (
            select(TrainingSession)
            .options(selectinload(TrainingSession.sets))
            .order_by(TrainingSession.date.desc(), TrainingSession.id.desc())
        )
        if limit:
            q = q.limit(limit)

        rows = db.execute(q).scalars().all()
        out: list[dict] = []
        for ts in rows:
            ssum = services.session_summary(ts, pace_per_m=pace_per_m)
            out.append({
                "id": ts.id,
                "date": ts.date.isoformat(),
                "notes": ts.notes,
                "total_distance_m": ssum["total_distance_m"],
                "avg_rpe": ssum["avg_rpe"],
                "avg_pace_sec_per": ssum["avg_pace_sec_per"],
                "pace_basis_m": ssum["pace_basis_m"],
                "avg_pace_formatted": ssum["avg_pace_formatted"],
            })
        return out
    finally:
        if owns:
            db.close()