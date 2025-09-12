import datetime as dt
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from sqlalchemy.orm import Session
from typing import Optional

from swimsmart.api.deps import get_db
from swimsmart.api.schemas import SessionDetailResponse, SessionAnalyticsResponse, CreatedSessionResponse, CreatedSetResponse, DashboardRow, RangeSummaryResponse, RangeListResponse
from swimsmart import crud
from swimsmart.schemas import SessionCreate, SetCreate

router = APIRouter()

@router.get("", response_model=list[DashboardRow])
def list_session(
    limit: Optional[int] = Query(None, ge=1, le=500),
    pace_per_m: int = Query(100),
    db: SetCreate = Depends(get_db),
) -> list[dict]:
    """
    Return a dashboard friendly, compact list withn computed summaries
    """
    rows = crud.list_sessions_with_summaries(limit=limit, pace_per_m=pace_per_m, db=db)
    return rows

@router.get("/range/summary", response_model=RangeSummaryResponse)
def summarise_session_range(
    start: dt.date = Query(..., description="Inclusive start date"),
    end: dt.date = Query(..., description= "Inclusive end date"),
    pace_per_m: int = Query(100),
    db: Session = Depends(get_db),
) -> dict:
    """
    Roll-up analytics across a date window.
    """
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    return crud.summarise_sessions(start, end, pace_per_m=pace_per_m, db=db)

@router.get("/range", response_model=RangeListResponse)
def list_sessions_in_range(
    start: dt.date = Query(...),
    end: dt.date = Query(...),
    pace_per_m: int = Query(100),
    db: Session = Depends(get_db),
) -> dict:
    """
    Returns:
    'session'; raw session(id/dates/notes) with minimal fields,
    'summary': uses servicess.sessions_summary.
    """
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start.")
    
    #pull ORM objects with sets
    sessions = crud.fetch_sessions_in_range(start, end, db=db)

    #shape tiny list for left pane
    short =  [{"id": s.id, "date": s.date.isoformat(), "notes": s.notes} for s in sessions]

    #compute roll-up
    summary = crud.summarise_sessions(start, end, pace_per_m=pace_per_m, db=db)

    return {"sessions": short, "summary": summary}

@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(session_id: int, db: Session = Depends(get_db)) -> dict:
    """
    Return one session with sets and totals
    """
    try:
       result = crud.get_session_detail(session_id, db=db)
    except ValueError:
        #CRUD raises value error when not found
        raise HTTPException(status_code=404, detail= "Session not found")
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result

@router.get("/{session_id}/analytics", response_model=SessionAnalyticsResponse)
def get_session_analytics(session_id: int, pace_per_m: int = 100, db: Session = Depends(get_db)) -> dict:
    """
    Return detail + summary + per-stroke breakdown + best set.
    """
    try:
        return crud.get_session_analytics(session_id, pace_per_m=pace_per_m, db=db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
    
@router.post("", response_model=CreatedSessionResponse)
def create_session(payload: SessionCreate,  db: Session = Depends(get_db)) -> dict:
    """
    Create session from Pydantic (date and optional notes).
    Returns lightweight dict for confirmation.
    """
    ts = crud.create_session(session_date=payload.date, notes=payload.notes, db=db)
    return {"id": ts.id, "date": ts.date.isoformat(), "notes":ts.notes}

@router.post("/{session_id}/sets", response_model=CreatedSetResponse)
def add_set_to_session(session_id: int, payload: SetCreate, db: Session = Depends(get_db)) -> dict:
    """
    Add a set to an existing session, uses SetCreate for validation.
    """
    try:
        s = crud.add_set(session_id, payload, db=db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"id": s.id, "session_id":s.session_id}
