from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from swimsmart.db import SessionLocal
from swimsmart.models import User
from swimsmart.auth import decode_token


def get_db():
    """
    FastAPI dependency, yields a database session as well as ensures that 
    the database is closed after request ends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
        authorization: str | None = Header(None),
        db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalide Authorization header")
    token = authorization.split("", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = int(payload.get("sub", 0))
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return User