"""Auth dependencies. get_current_customer_user restricts /portal/* (PDF
section 7's Technical Guidelines). get_current_internal_user is applied,
router-wide via `dependencies=` in api/main.py, to every internal-workspace
router except /auth and /portal itself -- PDF A1: "after login, internal
users can access backend configuration and open a sales workspace".
"""
import jwt
from fastapi import Depends, Header, HTTPException

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


def require_roles(*roles: str):
    """Dependency factory enforcing PS section 3's per-role write access
    (e.g. only Admin manages backend config; only Sales Manager/Finance
    decide approvals). The role claim is already embedded in the JWT at
    /auth/login (create_token includes "role"), so this needs no DB lookup.
    Use on MUTATION endpoints only -- GET/list endpoints stay open to any
    internal role so reps can still read products/warehouses/discount tiers
    while building a quote.
    """
    def _check(user: dict = Depends(get_current_internal_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {' or '.join(roles)}",
            )
        return user
    return _check
