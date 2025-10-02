import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from swimsmart.api.deps import get_db
from swimsmart.api.authz import get_current_user, require_roles
from swimsmart.models import TrainingSession, User, UserRole
from swimsmart.schemas import SessionCreate, SetCreate
from swimsmart.api.schemas import DashboardRow, RangeSummaryResponse, RangeListResponse, SessionDetailResponse, SessionAnalyticsResponse, CreatedSessionResponse, CreatedSetResponse
from swimsmart import crud

router = APIRouter()

def get_owned_session_or_403(db: Session, session_id: int, current_user: User) -> TrainingSession:
    """
    Load session and verify it belongs to current user.
    Raises 404 if not found or 403 if owned by someone else
    """
    ts =db.get(TrainingSession, session_id)
    if ts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    #check owner
    owner_id = ts.user_id
    if owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return ts

@router.get("/sessions", response_model=list[DashboardRow], dependencies=[Depends(require_roles(UserRole.swimmer))])
def list_my_sessions(
    limit: Optional[int] = Query(default=None, ge=1, le=500),
    pace_per_m: int = Query(default=100),
    db : Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ) -> list[dict]:
    """
    Swimmer-only: dashboard-friendly list of *my* sessions with summaries
    """
    #filters by current user id
    rows = crud.list_sessions_with_summaries(
        limit=limit,
        pace_per_m=pace_per_m,
        user_id=current_user.id,
        db=db
    )
    return rows

@router.get("/sessions/range/summary", response_model=RangeSummaryResponse, dependencies=[Depends(require_roles(UserRole.swimmer))])
def summarise_my_session_range(
    start: dt.date = Query(...,description="Inclusive start date"),
    end: dt.date = Query(...,description="Inclusive end date,"),
    pace_per_m: int = Query(default= 100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Swimmer-only: roll up analytics for my sessions across a desiered date range.
    """
    if end < start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end must be >= start")
    return crud.summarise_sessions(start, end, pace_per_m=pace_per_m, user_id=current_user.id, db=db)

@router.get("/sessions/range", response_model=RangeListResponse, dependencies=[Depends(require_roles(UserRole.swimmer))])
def list_my_sessions_in_range(
    start: dt.date = Query(...),
    end: dt.date = Query(...),
    pace_per_m: int = Query(default=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Raw list of my sessions in a date window + roll up summary.
    """
    if end < start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end must be >= start")
    
    # pull orm objects for my session
    sessions = crud.fetch_sessions_in_range(start, end, user_id=current_user.id, db=db)

    # Use loop to shape small list for left pane
    short: list[dict] = []
    for s in sessions:
        item = {"id": s.id, "date": s.date.isoformat(), "notes": s.notes}
        short.append(item)

    # compute roll up
    summary = crud.summarise_sessions(start, end, pace_per_m=pace_per_m, user_id=current_user.id, db=db)
    return {"sessions": short, "summary": summary}

@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, dependencies=[Depends(require_roles(UserRole.swimmer))])
def get_my_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    One of my sessions, with sets and totals.
    """
    check = get_owned_session_or_403(db, session_id, current_user)
    try:
        result = crud.get_session_detail(session_id, db=db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return result

@router.get("/sessions/{session_id}/analytics", response_model=SessionAnalyticsResponse, dependencies=[Depends(require_roles(UserRole.swimmer))])
def get_my_session_analytics(
    session_id: int,
    pace_per_m: int = Query(default=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    detail + summary + per-stroke-breakdown + best set
    """
    check = get_owned_session_or_403(db, session_id, current_user)
    try:
        return crud.get_session_analytics(session_id, pace_per_m=pace_per_m, db=db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
@router.post("/sessions", response_model=CreatedSessionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(UserRole.swimmer))])
def create_my_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Create a session owned by me
    """
    ts =crud.create_session(
        session_date = payload.date,
        notes = payload.notes,
        user_id = current_user.id,
        db = db
    )
    return {"id": ts.id, "date": ts.date.isoformat(), "notes": ts.notes}

@router.post("/sessions/{session_id}/sets", response_model=CreatedSetResponse, dependencies=[Depends(require_roles(UserRole.swimmer))])
def add_set_to_my_session(
    session_id: int,
    payload: SetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Add set to one of my sessions
    """
    check = get_owned_session_or_403(db, session_id, current_user)
    try:
        s = crud.add_set(session_id, payload, db=db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"id": s.id, "session_id": s.session_id}