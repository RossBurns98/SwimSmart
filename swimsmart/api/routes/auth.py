from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from swimsmart.api.deps import get_db
from swimsmart.schemas import Signup, Login
from swimsmart.models import User, UserRole
from swimsmart.auth import hash_password, verify_password, create_token

router = APIRouter()

@router.post("/signup")
def signup(payload: Signup, db: Session = Depends(get_db)) -> dict:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email Already Exists")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole(payload.role),
        username=payload.username
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role.value, "username": user.username}

@router.post("/login")
def login(payload: Login, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.identifier).first()
    if not user:
        user = db.query(User).filter(User.username == payload.identifier).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id, user.role.value)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role.value, "username":user.username}}
