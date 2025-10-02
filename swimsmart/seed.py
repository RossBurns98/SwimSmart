from __future__ import annotations
import argparse
import datetime as dt
import random
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from .models import User, UserRole, TrainingSession
from .auth import hash_password
from . import crud
from .schemas import SetCreate

DEFAULT_RNG_SEED = 1337

STROKES = ["free", "fly", "back", "breast", "im"]


def wipe_data(db: Session) -> None:
    """
    Delete rows from child -> parent order.
    Doesn't drop tables.
    """
    db.execute(text("DELETE FROM sets"))
    db.execute(text("DELETE FROM sessions"))
    db.execute(text("DELETE FROM users"))
    db.commit()


def ensure_coach(db: Session, email: str) -> User:
    """
    Creates a dummy coach with password if missing; ensures role is coach.
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password("changeme"),
            role=UserRole.coach,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # ensure coach role
        if user.role != UserRole.coach:
            user.role = UserRole.coach
            db.commit()          # <-- was missing parentheses
            db.refresh(user)
    return user


def create_swimmers(db: Session, count: int) -> list[User]:
    """
    Create N swimmers with predictable emails as well as password 'changeme'
    """
    swimmers: list[User] = []
    for i in range(count):
        email = f"swimmer{i+1}@example.com"
        existing = db.query(User).filter(User.email == email).first()
        if existing is None:
            u = User(
                email=email,
                password_hash=hash_password("changeme"),
                role=UserRole.swimmer,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            swimmers.append(u)
        else:
            if existing.role != UserRole.swimmer:
                existing.role = UserRole.swimmer
                db.commit()
                db.refresh(existing)
            swimmers.append(existing)
    return swimmers


def random_set_payload(rng: random.Random) -> SetCreate:
    """
    Build using SetCreate with realistic looking values.
    """
    possible_distances = [50, 75, 100, 150, 200, 400]
    distance_m = rng.choice(possible_distances)

    reps = rng.randint(2, 10)
    stroke = rng.choice(STROKES)

    # keep times between ~30s and 6 mins with a little jitter
    rep_times: list[int] = []
    for _ in range(reps):
        base = rng.randint(30, 360)
        jitter = rng.randint(-3, 5)
        t = max(10, min(3600, base + jitter))
        rep_times.append(t)

    max_rep = max(rep_times) if rep_times else 60
    interval_sec = max(10, min(3600, max_rep + rng.randint(5, 25)))

    rpe_list: list[int] = [rng.randint(4, 9) for _ in range(reps)]

    return SetCreate(
        distance_m=distance_m,
        reps=reps,
        interval_sec=interval_sec,
        stroke=stroke,
        rpe=rpe_list,
        rep_times_sec=rep_times,
    )


def seed_dataset(
    *,
    swimmers: int = 3,
    sessions_per_swimmer: int = 5,
    min_sets_per_session: int = 2,
    max_sets_per_session: int = 5,
    coach_email: str = "coach@example.com",
    start_date: Optional[dt.date] = None,
    days_span: int = 21,
    rng_seed: int = DEFAULT_RNG_SEED,
    reset: bool = False,
    db: Optional[Session] = None,        # <-- NEW: allow caller to pass the test session
) -> dict:
    """
    API for testing and scripts

    Creates:
      - 1 coach
      - N swimmers
      - M sessions per swimmer, across a given date window
      - 2-5 sets per session (configurable)

    Returns a dict summary.

    If `db` is provided, use it (so tests seed into their fixture DB).
    Otherwise create/close a local SessionLocal.
    """
    init_db()

    owns = db is None
    db = db or SessionLocal()

    try:
        if reset:
            wipe_data(db)

        rng = random.Random(rng_seed)

        coach = ensure_coach(db, coach_email)
        swimmer_users = create_swimmers(db, swimmers)

        # Date Plan: If none is given, use today - (days_span - 1)
        if start_date is None:
            start_date = dt.date.today() - dt.timedelta(days=days_span - 1)

        total_sessions = 0
        total_sets = 0

        # for each swimmer, create sessions across time window
        for sw in swimmer_users:
            for s_index in range(sessions_per_swimmer):
                # spread sessions across the window with a touch of jitter
                denom = max(1, sessions_per_swimmer)
                day_offset = int(round((s_index * (days_span - 1)) / denom))
                jitter = rng.randint(-1, 1)
                session_date = start_date + dt.timedelta(
                    days=max(0, min(days_span - 1, day_offset + jitter))
                )

                # Create session linked to swimmer
                ts = crud.create_session(
                    session_date=session_date,
                    notes=f"Session {s_index + 1} for {sw.email}",
                    user_id=sw.id,
                    db=db,
                )
                total_sessions += 1

                # Add sets
                set_count = rng.randint(min_sets_per_session, max_sets_per_session)
                for _ in range(set_count):
                    payload = random_set_payload(rng)
                    crud.add_set(ts.id, payload, db=db)
                    total_sets += 1

        return {
            "coach_id": coach.id,
            "swimmers": len(swimmer_users),
            "sessions": total_sessions,
            "sets": total_sets,
        }

    finally:
        if owns:
            db.close()


def main(argv: Optional[list[str]] = None) -> None:
    """
    CLI entrypoint: python -m swimsmart.seed [options]
    """
    parser = argparse.ArgumentParser(description="Seed the Swimsmart development database.")
    parser.add_argument("--swimmers", type=int, default=3, help="Number of swimmers to create.")
    parser.add_argument("--sessions", type=int, default=5, help="Sessions per swimmer.")
    parser.add_argument("--min-sets", type=int, default=2, help="Min sets per session.")
    parser.add_argument("--max-sets", type=int, default=5, help="Max sets per session.")
    parser.add_argument("--coach-email", type=str, default="coach@example.com", help="Coach email.")
    parser.add_argument("--days", type=int, default=21, help="Span of days to distribute sessions over.")
    parser.add_argument("--start", type=str, default=None, help="Start date YYYY-MM-DD; defaults to today - days+1.")
    parser.add_argument("--rng-seed", type=int, default=DEFAULT_RNG_SEED, help="Random seed.")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows before seeding.")

    args = parser.parse_args(argv)

    # For start date if provided
    start_date: Optional[dt.date] = None
    if args.start:
        try:
            start_date = dt.date.fromisoformat(args.start)
        except ValueError:
            raise SystemExit(f"Invalid --start date: {args.start!r}. Use YYYY-MM-DD")

    min_sets = max(1, args.min_sets)
    max_sets = max(min_sets, args.max_sets)

    summary = seed_dataset(
        swimmers=max(0, args.swimmers),
        sessions_per_swimmer=max(0, args.sessions),
        min_sets_per_session=min_sets,
        max_sets_per_session=max_sets,
        coach_email=args.coach_email,
        start_date=start_date,
        days_span=max(1, args.days),
        rng_seed=args.rng_seed,
        reset=args.reset,
        # CLI path uses its own SessionLocal (db=None)
    )
    print(
        f"Seed complete: coach_id={summary['coach_id']}, "
        f"swimmers={summary['swimmers']}, sessions={summary['sessions']}, sets={summary['sets']}"
    )


if __name__ == "__main__":
    main()
