from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import User, get_db
from api.auth_utils import create_token, hash_password, verify_password
from api.schemas import TokenOut, UserLoginIn, UserOut, UserSignupIn

router = APIRouter(tags=["auth"])

# Self-service signup can only request one of these roles -- "admin" is
# granted only by promotion (seed data or an existing Admin), never by
# signing up, so nobody can hand themselves the top access level.
SIGNUP_ROLES = {"sales_rep", "sales_manager", "finance"}


@router.post("/auth/signup", response_model=UserOut)
def signup(payload: UserSignupIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if payload.role not in SIGNUP_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of: {', '.join(sorted(SIGNUP_ROLES))}")
    user = User(
        name=payload.name, email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role, seniority=payload.seniority,
        status="pending",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenOut)
def login(payload: UserLoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.status == "pending":
        raise HTTPException(status_code=403, detail="Your account is awaiting admin approval.")
    if user.status == "rejected":
        raise HTTPException(status_code=403, detail="Your account request was rejected. Contact an admin.")
    token = create_token({"sub": str(user.id), "role": user.role, "type": "internal"})
    return TokenOut(access_token=token, user=user)
