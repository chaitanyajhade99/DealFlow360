from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import CreditNote, Subscription, SubscriptionPlan, get_db
from api.schemas import (
    CreditNoteOut,
    SubscriptionCancelIn,
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionPlanIn,
    SubscriptionPlanOut,
    SubscriptionUpdate,
)

router = APIRouter(tags=["subscriptions"])


@router.post("/subscriptions", response_model=SubscriptionOut)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    subscription = Subscription(**payload.model_dump())
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(db: Session = Depends(get_db)):
    return db.query(Subscription).all()


@router.get("/subscriptions/{id}", response_model=SubscriptionOut)
def get_subscription(id: int, db: Session = Depends(get_db)):
    subscription = db.get(Subscription, id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


@router.patch("/subscriptions/{id}", response_model=SubscriptionOut)
def update_subscription(id: int, payload: SubscriptionUpdate, db: Session = Depends(get_db)):
    """PDF B7: "Modify Subscription" — mid-cycle plan/cycle changes.
    Subscription has no qty/amount field to prorate a charge against; actual
    proration math lives in SubscriptionPlan.proration_rule for when that's
    wired to real billing.
    """
    subscription = db.get(Subscription, id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(subscription, key, value)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.post("/subscriptions/{id}/cancel", response_model=SubscriptionOut)
def cancel_subscription(id: int, payload: SubscriptionCancelIn, db: Session = Depends(get_db)):
    """PDF B7: "Cancel Subscription" with automatic partial refund / credit
    note trigger. refund_amount is caller-supplied since Subscription has no
    amount field to prorate from automatically.
    """
    subscription = db.get(Subscription, id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    subscription.status = "cancelled"
    if payload.refund_amount:
        db.add(CreditNote(
            subscription_id=id, amount=payload.refund_amount,
            reason=payload.reason or "Subscription cancelled",
        ))
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("/subscriptions/{id}/credit-notes", response_model=list[CreditNoteOut])
def list_subscription_credit_notes(id: int, db: Session = Depends(get_db)):
    return db.query(CreditNote).filter(CreditNote.subscription_id == id).all()


# ---- Subscription plan definitions (PDF A5) ----

@router.post("/subscription-plans", response_model=SubscriptionPlanOut)
def create_subscription_plan(payload: SubscriptionPlanIn, db: Session = Depends(get_db)):
    plan = SubscriptionPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/subscription-plans", response_model=list[SubscriptionPlanOut])
def list_subscription_plans(db: Session = Depends(get_db)):
    return db.query(SubscriptionPlan).all()
