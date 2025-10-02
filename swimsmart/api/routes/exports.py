from __future__ import annotations
import csv
import io
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session

from swimsmart.api.deps import get_db
from swimsmart.api.authz import get_current_user, require_roles, require_owner_or_coach_session
from swimsmart.models import User, UserRole, TrainingSession
from swimsmart import crud

router = APIRouter()

def rows_for_session(ts: TrainingSession) -> list[dict]:
    """
    Flatten a single TrainingSession into rows (one row per set)
    """
    rows: list[dict] = []
    for s in ts.sets or []:
        rows.append(
            {
                "session_id": ts.id,
                "date": ts.date.isoformat(),
                "notes": ts.notes or "",
                "owner_user_id": ts.user_id if ts.user_id is not None else "",
                "set_id": s.id,
                "distance_m": s.distance_m,
                "reps": s.reps,
                "interval_sec": s.interval_sec,
                "stroke": s.stroke or "",
                # trying to keep arrays intact
                "rpe": ",".join(str(x) for x in (s.rpe or [])),
                "rep_times_sec": ",".join(str(x) for x in (s.rep_times_sec or []))
            }
        )
    # for sessions with no sets: emits one row so CSV still has the session
    if not rows:
        rows.append(
            {
                "session_id": ts.id,
                "date": ts.date.isoformat(),
                "notes": ts.notes or "",
                "owner_user_id": ts.user_id if ts.user_id is not None else "",
                "set_id": "",
                "distance_m": "",
                "reps": "",
                "interval_sec": "",
                "stroke": "",
                "rpe": "",
                "rep_times_sec": ""
            }
        )
    return rows

def write_csv(rows: list[dict]) -> str:
    headers = [
        "session_id",
        "date",
        "notes",
        "owner_user_id",
        "set_id",
        "distance_m",
        "reps",
        "interval_sec",
        "stroke",
        "rpe",
        "rep_times_sec"
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()

@router.get("/session/{session_id}.csv", dependencies=[Depends(require_roles("swimmer", "coach"))])
def export_single_session_csv(
    session_id: int,
    bundle=Depends(require_owner_or_coach_session)
) -> Response:
    """
    Export one session (owner or coach only) as CSV rows
    """
    _user, ts = bundle
    csv_text = write_csv(rows_for_session(ts))
    filename = f"session_{ts.id}.csv"
    return Response(
        content= csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        status_code=status.HTTP_200_OK
    )

@router.get("/range.csv", dependencies=[Depends(require_roles("swimmer", "coach"))])
def export_range_csv(
    start: dt.date = Query(..., description="Inclusive start date"),
    end: dt.date = Query(..., description="Inclusive end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    swimmer_id: Optional[int] = Query(None, description="(Coach only) filter to a specific swimmer_id")
) -> Response:
    if end < start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end must be >= start")
    sessions = crud.fetch_sessions_in_range(start, end, db=db)
    filtered: list[TrainingSession] = []
    if current_user.role == UserRole.coach:
        for ts in sessions:
            if swimmer_id is None or ts.user_id == swimmer_id:
                filtered.append(ts)
    else:
        for ts in sessions:
            if ts.user_id == current_user.id:
                filtered.append(ts)
    all_rows: list[dict] = []
    for ts in filtered:
        for r in rows_for_session(ts):
            all_rows.append(r)
    csv_text = write_csv(all_rows)
    filename = f"sessions_{start.isoformat()}_{end.isoformat()}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        status_code=status.HTTP_200_OK
    )
