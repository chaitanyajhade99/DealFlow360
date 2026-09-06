from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import DiscountTier, get_db
from api.deps import require_roles
from api.schemas import DiscountTierIn, DiscountTierOut

router = APIRouter(tags=["discount-tiers"])

# PS section 3 gives this to BOTH roles: "Sales Manager / Approver ...
# Configures discount tiers and approval chains" and "Admin: Manages backend
# setup: ... discount tiers". Everyone else (Sales Rep, Finance) can read
# them (needed to build/review a quote) but not change policy.
_CAN_WRITE = require_roles("admin", "sales_manager")


@router.post("/discount-tiers", response_model=DiscountTierOut)
def create_discount_tier(payload: DiscountTierIn, db: Session = Depends(get_db), _=Depends(_CAN_WRITE)):
    tier = DiscountTier(**payload.model_dump())
    db.add(tier)
    db.commit()
    db.refresh(tier)
    return tier


@router.get("/discount-tiers", response_model=list[DiscountTierOut])
def list_discount_tiers(db: Session = Depends(get_db)):
    return db.query(DiscountTier).all()


@router.patch("/discount-tiers/{id}", response_model=DiscountTierOut)
def update_discount_tier(id: int, payload: DiscountTierIn, db: Session = Depends(get_db), _=Depends(_CAN_WRITE)):
    tier = db.get(DiscountTier, id)
    if not tier:
        raise HTTPException(status_code=404, detail="Discount tier not found")
    for key, value in payload.model_dump().items():
        setattr(tier, key, value)
    db.commit()
    db.refresh(tier)
    return tier
