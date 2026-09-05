"""Admin-only user governance. New internal accounts created via
POST /auth/signup start life as status="pending" and cannot log in until an
Admin approves them here -- prevents anyone who can reach the signup form
from granting themselves Sales Manager / Finance access unchecked.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import User, get_db
from api.deps import get_current_internal_user
from api.schemas import UserApprovalActionIn, UserOut

router = APIRouter(tags=["admin"])


def _require_admin(user=Depends(get_current_internal_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/admin/users", response_model=list[UserOut])
def list_users(
    status: str | None = Query(None, description="filter: pending / approved / rejected"),
    db: Session = Depends(get_db),
    _admin=Depends(_require_admin),
):
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    return query.order_by(User.id.desc()).all()


@router.post("/admin/users/{id}/approve", response_model=UserOut)
def approve_user(
    id: int, payload: UserApprovalActionIn = UserApprovalActionIn(),
    db: Session = Depends(get_db), _admin=Depends(_require_admin),
):
    user = db.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "approved"
    db.commit()
    db.refresh(user)
    return user


@router.post("/admin/users/{id}/reject", response_model=UserOut)
def reject_user(
    id: int, payload: UserApprovalActionIn = UserApprovalActionIn(),
    db: Session = Depends(get_db), _admin=Depends(_require_admin),
):
    user = db.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "rejected"
    db.commit()
    db.refresh(user)
    return user
