import datetime
from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
from typing import Literal, Optional

ALLOWED_STROKES = {"free", "fly", "back", "breast", "im"}

class SessionCreate(BaseModel):
    """Schema for new swim session creation.
    
    -'date': Required field here to log session date
    -'notes': Optional extra session info, can be left blank.
    """
    date: datetime.date = Field(..., description="Calendar date of the session (YYYY-MM-DD).")
    notes: str | None = Field(None, description="Optional Session Descriptor", max_length=2000)

class SetCreate(BaseModel):
    """Schema for new set creation

    Contains set distances, reps, intervals, rpe, stroke and rep time.
    New syntax; gt/ge = greater than/greater than or equal, lt/le = less than/less than or equal
    """
    distance_m: int = Field(..., gt=0,le=1500, description="Distance per rep in meters")
    reps: int = Field(..., ge=1, le = 50, description="Number of repetitions in the set")
    interval_sec: int = Field(..., ge=10, le=3600, description="Time each rep must be completed in.")
    rpe: list[int] = Field(..., description="Rate of Perceived Exertion(How hard you found each rep, on a scale from 1 to 10.)")
    stroke: str = Field(..., description="What stroke was done during this set? (Free, Fly, Back, Breast, IM)")
    rep_times_sec: list[int] = Field(..., description="List of times per rep in seconds")

    @field_validator("stroke")
    @classmethod
    def normalise_and_validate_stroke(cls, v: str) -> str:
        if v is None:
            raise ValueError("Stroke is required.")
        value = str(v).strip().lower()
        if value not in ALLOWED_STROKES:
            allowed_str = ", ".join(sorted(ALLOWED_STROKES))
            raise ValueError(f"stoke must be one of: {allowed_str}")
        return value

    @field_validator("rpe")
    @classmethod
    def validate_rpe_values(cls, v: list[int]) -> list[int]:
        for i, val in enumerate(v):
            if not (1<= val <= 10):
                raise ValueError(f"rpe number {i} must be between 1 and 10 (got {val})")
        return v
    
    @field_validator("rep_times_sec")
    @classmethod
    def validate_rep_times(cls, v: list[int]) -> list[int]:
        for i, val in enumerate(v):
            if not (10 <= val <= 3600):
                raise ValueError(f"input number {i} was outside the range for a normal time (10 to 3600 seconds)")
        return v
    
    @model_validator(mode="after")
    def list_length_check(self)-> "SetCreate":
        if self.reps != len(self.rpe):
            raise ValueError(f"Expected {self.reps} RPE inputs, got {len(self.rpe)}.")
        if self.reps != len(self.rep_times_sec):
            raise ValueError(f"Expected {self.reps} rep time inputs, got {len(self.rep_times_sec)}.")
        return self
    
class Signup(BaseModel):
    email: EmailStr
    password: str
    role: str
    username: Optional[str] = None
    invite_code: str

class Login(BaseModel):
    identifier: str
    password: str
