from __future__ import annotations

from typing import Callable, Tuple
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from swimsmart.api.deps import get_db
from swimsmart.auth import decode_token
from swimsmart.models import User, UserRole, TrainingSession


def extract_bearer_token(auth_header: str | None) -> str:
    """
    Pull JWT out of Authorization header: 'Bearer <token>'
    - tolerant of extra spaces
    - tolerant if user accidentally sends 'Bearer Bearer <token>'
    """
    if auth_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header.",
        )
    parts = auth_header.split()
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format.",
        )
    if parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization scheme must be Bearer.",
        )
    # take the last chunk to survive "Bearer Bearer <token>"
    return parts[-1]


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> User:
    token = extract_bearer_token(authorization)
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    sub = payload.get("sub")
    try:
        user_id = int(sub)  # accept "1" or 1
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not found.")
    return user


def require_roles(*allowed: UserRole | str) -> Callable[[User], User]:
    """
    Ensure current user has one of the allowed roles.
    If none provided, defaults to {"coach", "swimmer"}.
    """
    allowed_values: set[str] = set()
    if not allowed:
        allowed_values.update({"coach", "swimmer"})
    else:
        for item in allowed:
            allowed_values.add(item.value if isinstance(item, UserRole) else str(item))

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role.",
            )
        return user

    return _dep


def require_owner_or_coach_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tuple[User, TrainingSession]:
    """
    Ensure current user is the owner of the session or they are a coach.
    Returns (user, TrainingSession) for endpoint usage.
    """
    ts = db.get(TrainingSession, session_id)
    if ts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if user.role == UserRole.coach:
        return (user, ts)

    if ts.user_id is not None and ts.user_id == user.id:
        return (user, ts)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden.",
    )
