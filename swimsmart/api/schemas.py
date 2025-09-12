from __future__ import annotations
import datetime as dt
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class DateRangeQuery(BaseModel):
    start: dt.date = Field(..., description="Inclusive start date (YYYY-MM-DD)")
    end: dt.date = Field(..., description="Inclusive end date (YYYY-MM-DD)")

class DashboardQuery(BaseModel):
    limit: int = Field(10, ge=1, le=500, description="Max rows to return")
    pace_per_m: int = Field(100, description="Split Basis (e.g., 25/50/75/100)")

#Detail shapes
class SessionDetailSet(BaseModel):
    id: int
    distance_m: int
    reps: int
    interval_sec: int
    stroke: str
    rpe: List[int]
    rep_times_sec: List[int]

class SessionTotals(BaseModel):
    total_sets: int
    total_distance_m: float
    total_reps: float
    avg_rpe: Optional[float]
    avg_rep_time_sec: Optional[float]

class SessionDetailResponse(BaseModel):
    id: int
    date: str
    notes: Optional[str]
    sets: List[SessionDetailSet]
    totals: SessionTotals

#Summary Shapes
class SessionSummaryResponse(BaseModel):
    total_distance_m: float
    avg_rpe: Optional[float]
    avg_pace_sec_per: Optional[float]
    pace_basis_m: int
    avg_pace_formatted: Optional[str]

class StrokeBreakdownItem(BaseModel):
    total_distance_m: float
    avg_pace_sec_per: Optional[float]
    avg_pace_formatted: Optional[str]

class SessionAnalyticsResponse(BaseModel):
    detail: SessionDetailResponse
    summary: SessionSummaryResponse
    by_stroke: Dict[str, StrokeBreakdownItem]
    best_set: Optional[dict]

#Create Response
class CreatedSessionResponse(BaseModel):
    id: int
    date: str
    notes: Optional[str]

class CreatedSetResponse(BaseModel):
    id: int
    session_id: int

# Dashboard and Ranges
class DashboardRow(BaseModel):
    id: int
    date: str
    notes: Optional[str]
    total_distance_m: float
    avg_rpe: Optional[float]
    avg_pace_sec_per: Optional[float]
    pace_basis_m: int
    avg_pace_formatted: Optional[str]

class RangeSummaryResponse(BaseModel):
    sessions: int
    total_distance_m: float
    avg_rpe: Optional[float]
    avg_pace_sec_per: Optional[float]
    pace_basis_m: int
    avg_pace_formatted: Optional[str]

class RangeListResponse(BaseModel):
    sessions: List[dict] #small dicts {id, date, notes}
    summary: RangeSummaryResponse
