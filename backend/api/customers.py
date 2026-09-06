"""Customer directory for the internal workspace. The quotation builder
(PDF B2) picks a customer from here instead of letting a Sales Rep type a
free-text name/tier by hand -- name and tier ride along automatically once a
customer is selected, and tier itself is never manually set (see
api.tiering.recalc_customer_tier -- it's earned from closed order volume).

Approval gate (see models.Customer.status): a company created here by an
internal user is auto-"approved" (an employee already vetted it), but one
created via self-service POST /portal/signup starts "pending" and is
excluded from the default listing below until an Admin approves it --
see admin_customers.py for that queue.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Customer, get_db
from api.schemas import CustomerIn, CustomerOut

router = APIRouter(tags=["customers"])


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(
    status: str | None = Query(
        "approved", description="pending / approved / rejected / all -- defaults to approved-only"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Customer)
    if status and status != "all":
        query = query.filter(Customer.status == status)
    return query.order_by(Customer.name).all()


@router.post("/customers", response_model=CustomerOut)
def create_customer(payload: CustomerIn, db: Session = Depends(get_db)):
    """Onboards a brand-new customer organization -- separate from building
    a quote for one. Always starts at Bronze tier, auto-approved (an
    internal user is creating it, unlike self-service portal signup).

    Matching is case-insensitive so "TCS" and "tcs" resolve to one company.
    If a customer with this name already exists but is still pending/rejected
    (e.g. it came from a self-service /portal/signup nobody has vetted yet),
    an internal user creating it here IS the vetting step -- so it gets
    claimed and flipped to approved instead of blocking with a 400. Only a
    name that's already approved is treated as a genuine duplicate.
    """
    existing = db.query(Customer).filter(func.lower(Customer.name) == payload.name.lower()).first()
    if existing:
        if existing.status == "approved":
            raise HTTPException(status_code=400, detail="A customer with this name already exists")
        existing.status = "approved"
        db.commit()
        db.refresh(existing)
        return existing
    customer = Customer(name=payload.name, default_tier="Bronze", status="approved")
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
