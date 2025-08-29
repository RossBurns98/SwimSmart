import pytest
from swimsmart.schemas import SessionCreate, SetCreate

def test_set_create_valid():
    set_obj = SetCreate(
        distance_m=100,
        reps=3,
        interval_sec=60,
        rpe=[5, 6, 7],
        stroke="Free",
        rep_times_sec=[65, 66, 67],
    )
    assert set_obj.reps == 3
    assert set_obj.rpe[0] == 5

def test_set_create_rpe_out_of_range():
    with pytest.raises(ValueError) as exc:
        SetCreate(
            distance_m=100,
            reps=3,
            interval_sec=60,
            rpe=[5, 6, 11],  # 11 is invalid
            stroke="Free",
            rep_times_sec=[65, 66, 67],
        )
    assert "rpe" in str(exc.value)


def test_session_create_valid_date_and_optional_notes():
    # Pydantic should parse the ISO string into a datetime.date
    s = SessionCreate(date="2025-08-29", notes="Taper week #easy")
    assert str(s.date) == "2025-08-29"
    assert s.notes == "Taper week #easy"

def test_session_create_bad_date_format_raises():
    # Invalid date string should fail validation
    with pytest.raises(ValueError):
        SessionCreate(date="29-08-2025", notes=None)