import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from swimsmart.api.deps import get_db
from swimsmart.schemas import Signup, Login
from swimsmart.models import User, UserRole
from swimsmart.auth import hash_password, verify_password, create_token

router = APIRouter()

COACH_INVITE_CODE = os.getenv("COACH_INVITE_CODE")
SWIMMER_INVITE_CODE = os.getenv("SWIMMER_INVITE_CODE")

@router.post("/signup")
def signup(payload: Signup, db: Session = Depends(get_db)) -> dict:
    role_norm = (payload.role or "").strip().lower()
    if role_norm not in {"coach", "swimmer"}:
        raise HTTPException(status_code=400, detail="Invalid role.")
    if not payload.invite_code or not payload.invite_code.strip():
        raise HTTPException(status_code=400, detail="Invite code is required.")
    expected = COACH_INVITE_CODE if role_norm == "coach" else SWIMMER_INVITE_CODE
    if not expected or payload.invite_code != expected:
        if role_norm == "coach":
            raise HTTPException(status_code=400, detail="Invalid invite code for coach.")
        else:
            raise HTTPException(status_code=400, detail="Invalid invite code for swimmer.")
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email Already Exists")
    username_val = (payload.username or "").strip() or None
    if username_val:
        taken = db.query(User).filter(User.username == username_val).first()
        if taken:
            raise HTTPException(status_code=409, detail="Username Already Exists")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole(role_norm),
        username=username_val
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "ok"}

@router.post("/login")
def login(payload: Login, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.identifier).first()
    if not user:
        user = db.query(User).filter(User.username == payload.identifier).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id, user.role.value)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role.value, "username":user.username}}
