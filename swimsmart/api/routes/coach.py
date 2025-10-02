import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from swimsmart.api.deps import get_db
from swimsmart.api.authz import require_roles, get_current_user
from swimsmart.models import User, UserRole, TrainingSession
from swimsmart.schemas import SessionCreate, SetCreate
from swimsmart.api.schemas import DashboardRow, SessionDetailResponse, SessionAnalyticsResponse, CreatedSessionResponse, CreatedSetResponse
from swimsmart import crud

router = APIRouter()

def get_swimmer_or_404(swimmer_id: int, db: Session) -> User:
    swimmer = db.get(User, swimmer_id)
    if swimmer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Swimmer not found.")
    if swimmer.role != UserRole.swimmer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a swimmer.")
    return swimmer

def get_session_or_404(session_id: int, db: Session) -> TrainingSession:
    ts = db.get(TrainingSession, session_id)
    if ts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return ts

def assert_session_belongs_to_swimmer(ts: TrainingSession, swimmer_id: int) -> None:
    """
    Coach helper, esures session's owner matches swimmer_id.
    Returs 409 error if mismatch.
    """
    if ts.user_id != swimmer_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session doesn't belong to this swimmer.")
    
@router.get("/swimmers", dependencies=[Depends(require_roles("coach"))])
def list_swimmers(db: Session = Depends(get_db)) -> list[dict]:
    """
    Return all users with swimmer role. (id and email)
    """
    rows = db.query(User).filter(User.role == UserRole.swimmer).all()
    out: list[dict] = []
    for u in rows:
        item = {"id": u.id, "email": u.email}
        out.append(item)
    return out

@router.get("/swimmers/{swimmer_id}/sessions", response_model=list[DashboardRow], dependencies=[Depends(require_roles("coach"))])
def list_swimmer_sessions(swimmer_id: int, pace_per_m: int = Query(100), limit: Optional[int] = Query(None, ge=1, le=500), db: Session = Depends(get_db)) -> list[dict]:
    """
    Dashboard list of a single swimmers sessions with summaries.
    """
    get_swimmer_or_404(swimmer_id, db)

    rows = crud.list_sessions_with_summaries(user_id=swimmer_id, limit=limit, pace_per_m=pace_per_m, db=db)
    return rows

@router.post("/swimmers/{swimmer_id}/sessions", response_model=CreatedSessionResponse, dependencies=[Depends(require_roles("coach"))], status_code=status.HTTP_201_CREATED)
def coach_create_session_for_swimmer(swimmer_id: int, payload: SessionCreate, db: Session = Depends(get_db)) -> dict:
    """
    Allows coach to make a session for a swimmer. (owner will be swimmer)
    """
    get_swimmer_or_404(swimmer_id, db)

    ts = crud.create_session(
        session_date=payload.date,
        notes= payload.notes,
        user_id=swimmer_id,
        db=db)
    return {"id": ts.id, "date": ts.date.isoformat(), "notes": ts.notes}

@router.get("/swimmers/{swimmer_id}/sessions/{session_id}", response_model=SessionDetailResponse, dependencies=[Depends(require_roles("coach"))])
def coach_get_swimmer_session_detail(
    swimmer_id: int,
    session_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Coach gets swimmer's session detail. Confirms correct swimmer_id ownership.
    """
    ts = get_session_or_404(session_id, db)

    if ts.user_id != swimmer_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session doesn't belong to this swimmer")

    get_swimmer_or_404(swimmer_id, db)

    assert_session_belongs_to_swimmer(ts, swimmer_id)

    try:
        detail = crud.get_session_detail(session_id, db=db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return detail

@router.get("/swimmers/{swimmer_id}/sessions/{session_id}/analytics", response_model=SessionAnalyticsResponse, dependencies=[Depends(require_roles("coach"))])
def coach_get_swimmer_session_analytics(
    swimmer_id: int,
    session_id: int,
    pace_per_m: int = Query(100),
    db: Session = Depends(get_db)
) -> dict:
    """
    Coach grabs detail + analytics for a swimmer's session
    """
    ts = get_session_or_404(session_id, db)

    if ts.user_id != swimmer_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session doesn't belong to this swimmer.")

    get_swimmer_or_404(swimmer_id, db)
    
    assert_session_belongs_to_swimmer(ts, swimmer_id)

    try:
        return crud.get_session_analytics(session_id, pace_per_m=pace_per_m, db=db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    
@router.post("/swimmers/{swimmer_id}/sessions/{session_id}/sets", response_model=CreatedSetResponse, dependencies=[Depends(require_roles("coach"))])
def coach_add_set_to_swimmer_session(swimmer_id: int, session_id: int, payload: SetCreate, db: Session = Depends(get_db)) -> dict:
    """
    Coach adds a set to a swimmer's session.
    Verifies the session belongs to the swimmer.
    """
    get_swimmer_or_404(swimmer_id, db)
    ts = get_session_or_404(session_id, db)
    assert_session_belongs_to_swimmer(ts, swimmer_id)

    try:
        s = crud.add_set(session_id, payload, db=db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    
    return {"id": s.id, "session_id": s.session_id}

@router.get("/overview", dependencies=[Depends(require_roles("coach"))])
def coach_overview(
    pace_per_m: int = Query(100),
    limit_per_swimmer: Optional[int] = Query(3, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict:
    """
    Returns a multi-swimmer overview.
    """
    swimmers = db.query(User).filter(User.role == UserRole.swimmer).all()
    out_swimmers: list[dict] = []

    for u in swimmers:
        recent = crud.list_sessions_with_summaries_for_user(
            user_id=u.id,
            limit=limit_per_swimmer,
            pace_per_m=pace_per_m,
            db=db,
        )
        entry = {
            "id": u.id,
            "email": u.email,
            "recent_sessions": recent,
        }
        out_swimmers.append(entry)

    return {"swimmers": out_swimmers}


@router.get("/leaderboard", dependencies=[Depends(require_roles("coach"))])
def coach_leaderboard(
    start: dt.date = Query(..., description="Inclusive start date"),
    end: dt.date = Query(..., description="Inclusive end date"),
    pace_per_m: int = Query(100),
    db: Session = Depends(get_db),
) -> dict:
    """
    Returns a leaderboard of swimmers by total distance
    """
    if end < start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end must be >= start")

    rows = crud.team_leaderboard_by_distance(
        start_date=start,
        end_date=end,
        pace_per_m=pace_per_m,
        db=db,
    )
    return {"start": start.isoformat(), "end": end.isoformat(), "rows": rows}