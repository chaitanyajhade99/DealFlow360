from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import CreditNote, Subscription, SubscriptionPlan, get_db
from api.deps import require_roles
from api.schemas import (
    CreditNoteOut,
    SubscriptionCancelIn,
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionPlanIn,
    SubscriptionPlanOut,
    SubscriptionUpdate,
    SubscriptionUpdateOut,
)

router = APIRouter(tags=["subscriptions"])

# PDF A5: "monthly, quarterly, yearly" -- fixed day-counts, not calendar-exact,
# which is the standard simplification for proration math without a real
# billing calendar.
CYCLE_DAYS = {"Monthly": 30, "Quarterly": 90, "Yearly": 365}


def _cycle_days(cycle: str | None) -> int:
    return CYCLE_DAYS.get(cycle or "", 30)


def _days_remaining(subscription: Subscription) -> int:
    if not subscription.next_bill_date:
        return _cycle_days(subscription.cycle)
    return max((subscription.next_bill_date - date.today()).days, 0)


@router.post("/subscriptions", response_model=SubscriptionOut)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    subscription = Subscription(**payload.model_dump())
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(
    quotation_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Subscription)
    if quotation_id is not None:
        query = query.filter(Subscription.quotation_id == quotation_id)
    if status is not None:
        query = query.filter(Subscription.status == status)
    return query.all()


@router.get("/subscriptions/{id}", response_model=SubscriptionOut)
def get_subscription(id: int, db: Session = Depends(get_db)):
    subscription = db.get(Subscription, id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


@router.patch("/subscriptions/{id}", response_model=SubscriptionUpdateOut)
def update_subscription(id: int, payload: SubscriptionUpdate, db: Session = Depends(get_db)):
    """PDF B7: "Modify Subscription" — mid-cycle plan/qty/amount changes.

    Real proration: the amount delta (new - old) is scaled by the fraction of
    the current billing cycle remaining. A downgrade (negative proration)
    auto-creates a CreditNote, mirroring cancel's behaviour. An upgrade
    (positive proration) is reported but not auto-invoiced -- raise that
    manually via POST /invoices, since Invoice requires a quotation_id and a
    subscription may exist without one.
    """
    subscription = db.get(Subscription, id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    old_amount = float(subscription.amount) if subscription.amount is not None else None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(subscription, key, value)
    new_amount = float(subscription.amount) if subscription.amount is not None else None

    proration_amount = None
    credit_note = None
    if old_amount is not None and new_amount is not None and old_amount != new_amount:
        days_remaining = _days_remaining(subscription)
        cycle_days = _cycle_days(subscription.cycle)
        proration_amount = round((new_amount - old_amount) * (days_remaining / cycle_days), 2)
        if proration_amount < 0:
            credit_note = CreditNote(
                subscription_id=id, amount=abs(proration_amount),
                reason="Prorated downgrade on subscription modify",
            )
            db.add(credit_note)

    db.commit()
    db.refresh(subscription)
    if credit_note:
        db.refresh(credit_note)
    return SubscriptionUpdateOut(
        subscription=subscription, proration_amount=proration_amount, credit_note=credit_note,
    )


@router.post("/subscriptions/{id}/cancel", response_model=SubscriptionOut)
def cancel_subscription(id: int, payload: SubscriptionCancelIn, db: Session = Depends(get_db)):
    """PDF B7: "Cancel Subscription" with automatic partial refund / credit
    note trigger. If refund_amount isn't supplied, it's computed as
    amount * (days_remaining_in_cycle / cycle_length_days) when the
    subscription has both amount and next_bill_date set; otherwise no refund
    is created (there's nothing to prorate from).
    """
    subscription = db.get(Subscription, id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    subscription.status = "cancelled"

    refund_amount = payload.refund_amount
    if refund_amount is None and subscription.amount is not None:
        days_remaining = _days_remaining(subscription)
        cycle_days = _cycle_days(subscription.cycle)
        refund_amount = round(float(subscription.amount) * (days_remaining / cycle_days), 2)

    if refund_amount:
        db.add(CreditNote(
            subscription_id=id, amount=refund_amount,
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
def create_subscription_plan(payload: SubscriptionPlanIn, db: Session = Depends(get_db), _admin=Depends(require_roles("admin"))):
    plan = SubscriptionPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/subscription-plans", response_model=list[SubscriptionPlanOut])
def list_subscription_plans(db: Session = Depends(get_db)):
    return db.query(SubscriptionPlan).all()
