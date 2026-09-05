"""Auth dependencies. Applied to /portal/* (customer-facing, must be
restricted per PDF section 7's Technical Guidelines). NOT retrofitted onto
the existing internal endpoints yet — that would be a breaking change for
already-integrated frontend calls; flagged in API_CONTRACT.md as a follow-up.
"""
import jwt
from fastapi import Header, HTTPException

from api.auth_utils import decode_token


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ")


def get_current_customer_user(authorization: str | None = Header(default=None)) -> dict:
    token = _bearer_token(authorization)
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "customer":
        raise HTTPException(status_code=403, detail="Not a customer portal token")
    return payload


def get_current_internal_user(authorization: str | None = Header(default=None)) -> dict:
    token = _bearer_token(authorization)
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "internal":
        raise HTTPException(status_code=403, detail="Not an internal user token")
    return payload
