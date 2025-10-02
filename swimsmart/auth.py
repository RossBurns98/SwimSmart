import os
import datetime as dt
import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("SWIMSMART_JWT_SECRET", "CHANGE_ME_DEV_ONLY")
JWT_ALGORITHM = os.getenv("SWIMSMART_JWT_ALGORITHM", "HS256")
JWT_EXPIRE_SEC = int(os.getenv("SWIMSMART_JWT_EXPIRE_SEC", "28800"))

# Use PBKDF2 (no bcrypt dependency problems)
_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(pw: str) -> str:
    return _pwd.hash(pw)

def verify_password(pw: str, pw_hash: str) -> bool:
    return _pwd.verify(pw, pw_hash)

def create_token(sub: int, role: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(sub),  # keep this as INT to match authz expectations
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(seconds=JWT_EXPIRE_SEC)).timestamp()),
        "jti": os.urandom(8).hex(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
