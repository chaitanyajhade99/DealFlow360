"""Password hashing and JWT helpers shared by /auth (internal users) and
/portal (customer portal users).
"""
import datetime
import os

import bcrypt
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production-please-32b")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, AttributeError):
        return False


def create_token(claims: dict, expiry_hours: float = JWT_EXPIRY_HOURS) -> str:
    payload = {
        **claims,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=expiry_hours),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
