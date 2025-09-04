import datetime as dt

from swimsmart import crud, services
from swimsmart.schemas import SetCreate
from swimsmart.db import SessionLocal

# open a DB session
db = SessionLocal()

# 1. create a training session
ts = crud.create_session(session_date=dt.date(2025, 1, 1), notes="Morning swim", db=db)

# 2. add some sets
set1 = SetCreate(distance_m=100, reps=4, interval_sec=90, stroke="free",
                 rpe=[5,6,6,5], rep_times_sec=[75,76,77,75])
set2 = SetCreate(distance_m=50, reps=6, interval_sec=60, stroke="fly",
                 rpe=[7,7,8,7,7,7], rep_times_sec=[40,41,42,40,41,40])
crud.add_set(ts.id, set1, db=db)
crud.add_set(ts.id, set2, db=db)

# 3. fetch full detail
detail = crud.get_session_detail(ts.id, db=db)
print("DETAIL:", detail)

# 4. run service functions
summary = services.session_summary(ts)
print("SUMMARY:", summary)

breakdown = services.stroke_breakdown(ts)
print("BY STROKE:", breakdown)

best_set = services.best_set_pace(ts)
print("BEST SET:", best_set)

db.close()
