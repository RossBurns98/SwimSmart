from __future__ import annotations
import datetime as dt
from pydantic import BaseModel, Field

class DateRangeQuery(BaseModel):
    start: dt.date = Field(..., description="Inclusive start date (YYYY-MM-DD)")
    end: dt.date = Field(..., description="Inclusive end date (YYYY-MM-DD)")

class DashboardQuery(BaseModel):
    limit: int = Field(10, ge=1, le=500, description="Max rows to return")
    pace_per_m: int = Field(100, description="Split Basis (e.g., 25/50/75/100)")