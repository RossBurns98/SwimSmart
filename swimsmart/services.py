from __future__ import annotations
from typing import Optional
from .models import TrainingSession

def calculate_pace_per(distance_m: float | int, time_sec: float | int, per_m: float | int = 100) -> Optional[float]:
    """ 
    Returns pace for a desired split distance (25m/50m/75m/100m) 
    Checks if missing or zero value, if so returns None
    """
    if not distance_m or not time_sec or not per_m:
        return None
    return (float(time_sec)/float(distance_m))*float(per_m)


#making a nicer time format
def format_seconds_mm_ss(seconds: Optional[float]) -> Optional[str]:
    """
    Convert seconds (e.g., 78.14) into '1:18.14' style.
    Returns None if input is None.
    """
    if seconds is None:
        return None

    # Round to hundredths first, then split into m:ss.hh
    total_hundredths = int(round(float(seconds) * 100))

    minutes = total_hundredths // (60 * 100)
    rem = total_hundredths % (60 * 100)
    secs = rem // 100
    hundredths = rem % 100

    return f"{minutes}:{secs:02d}.{hundredths:02d}"

def session_summary(session: TrainingSession,  pace_per_m: int = 100) -> dict:
    """
    Computes a summary of a session and returns a compact form like:

    {
      "total_distance_m": float,
      "avg_rpe": float | None,
      "avg_pace_sec_per": float | None, 
      "pace_basis_m": int,                
      "avg_pace_formatted": str | None,  
    }
    """

    sets = session.sets or []

    # first getting totals for dist and reps
    total_distance_m = 0.0
    for s in sets:
        total_distance_m += s.distance_m * s.reps

    # averging arrays per rep
    all_rpe: list[float] = []
    for s in sets:
        rpes = s.rpe or []
        for x in rpes:
            all_rpe.append(x)
    
    if all_rpe:
        avg_rpe = round(sum(all_rpe) / len(all_rpe),2)
    else:
        avg_rpe = None
    
    # finding total time and working out average across
    total_time_sec = 0.0
    for s in sets:
        times = s.rep_times_sec or []
        for t in times:
            total_time_sec += float(t)

    #getting split pace
    avg_pace = None
    if total_distance_m > 0 and total_time_sec > 0:
        avg_pace = calculate_pace_per(total_distance_m, total_time_sec, pace_per_m)
        if avg_pace is not None:
            avg_pace = round(avg_pace, 2)
        
    return {
        "total_distance_m": float(total_distance_m),
        "avg_rpe": avg_rpe,
        # nicer to use in code
        "avg_pace_sec_per": avg_pace,
        "pace_basis_m": pace_per_m,
        # Nice looking string for display purpose
        "avg_pace_formatted": format_seconds_mm_ss(avg_pace),
    }