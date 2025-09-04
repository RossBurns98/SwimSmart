from __future__ import annotations
from typing import Optional
from .models import TrainingSession
from collections import defaultdict

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

def stroke_breakdown(session, pace_per_m: int = 100) -> dict:
    """
    Totals for each stroke and average pace per stroke for a given split where possible.
    """

    sets = session.sets or []

    by_stroke = defaultdict(lambda: {
        "total_distance_m": 0.0, # sum of distance per stroke
        "total_time_sec": 0.0, # sum of time per stroke
    })

    # collecting distances for each stroke
    for s in sets:
        stroke = s.stroke or "unknown" # covers case where no listed stroke
        by_stroke[stroke]["total_distance_m"] += float(s.distance_m * s.reps)
    
    #collects times for each stroke
        times = s.rep_times_sec or []
        for t in times:
            by_stroke[stroke]["total_time_sec"] += float(t)

    #compute pace per stroke for output(out)
    out = {}
    for stroke, agg in by_stroke.items():
        dist = agg["total_distance_m"]
        total_time = agg["total_time_sec"]

        pace = None
        if dist > 0 and total_time > 0:
            pace = calculate_pace_per(dist, total_time, pace_per_m)
            if pace is not None:
                pace = round(pace, 2)
        
        out[stroke] = {
            "total_distance_m": dist,
            "avg_pace_sec_per": pace,
            "avg_pace_formatted": format_seconds_mm_ss(pace)
        }
    
    return out

def best_set_pace(session, pace_per_m: int = 100) -> Optional[dict]:
    """
    Finds fastest set, Returns a dict with set details.
    If no timing data, returns None.
    """
    sets = session.sets or []
    best = None

    for s in sets:
        set_distance = float(s.distance_m * s.reps)
        if set_distance <= 0:
            continue

        total_time = 0.0
        times = s.rep_times_sec or []
        for t in times:
            total_time += float(t)
        if total_time <= 0:
            continue

        pace = calculate_pace_per(set_distance, total_time, pace_per_m)
        if pace is None:
            continue
        pace = round(pace, 2)

        candidate = {
            "set_id": s.id,
            "stroke": s.stroke,
            "distance_m": s.distance_m,
            "reps": s.reps,
            "pace_sec_per": pace,
            "pace_formatted": format_seconds_mm_ss(pace),
        }

        if best is None or candidate["pace_sec_per"] < best["pace_sec_per"]:
            best = candidate
    
    return best

def sessions_summary(sessions: list, pace_per_m: int = 100) -> dict:
    """
    Gives stats for total session like:
    - total distance
    - average rpe
    - average pace wrt distance
    """

    total_distance_m = 0.0
    all_rpe = []
    total_time_sec = 0.0
    session_count = 0

    for sesh in sessions or []:
        session_count += 1
        sets = sesh.sets or []

        for s in sets:
            total_distance_m += float(s.distance_m * s.reps)
        
        for s in sets:
            rpes = s.rpe or []
            for x in rpes:
                all_rpe.append(float(x))
        
        for s in sets:
            times = s.rep_times_sec or []
            for t in times:
                total_time_sec += float(t)
    
    avg_rpe = round(sum(all_rpe) / len(all_rpe), 2) if all_rpe else None
    
    avg_pace = None
    if total_distance_m > 0 and total_time_sec > 0:
        avg_pace = calculate_pace_per(total_distance_m, total_time_sec, pace_per_m)
        if avg_pace is not None:
            avg_pace = round(avg_pace, 2)
    
    return {
        "sessions": session_count,
        "total_distance_m": total_distance_m,
        "avg_rpe": avg_rpe,
        "avg_pace_sec_per": avg_pace,
        "pace_basis_m": pace_per_m,
        "avg_pace_formatted": format_seconds_mm_ss(avg_pace),
    }