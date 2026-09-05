"""Customer-facing portal (PDF B8) — separate, restricted from the internal
workspace per section 7's Technical Guidelines. Every route here requires a
customer-type JWT (get_current_customer_user), never an internal one.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import Customer, CustomerUser, NegotiationRequest, Quotation, QuotationLine, get_db
from api.auth_utils import create_token, hash_password, verify_password
from api.deps import get_current_customer_user
from api.quotations import _attach_margins, _attach_product_names, score_and_route
from api.schemas import (
    ApprovalOut,
    CustomerOut,
    CustomerSignupIn,
    CustomerUserOut,
    NegotiationRequestIn,
    NegotiationRequestOut,
    PortalLoginIn,
    PortalMagicLinkIn,
    PortalMagicLinkOut,
    PortalMeOut,
    PortalTokenOut,
    QuotationOut,
)

router = APIRouter(tags=["customer-portal"])


def _customer_or_404(db: Session, customer_payload: dict) -> Customer:
    customer = db.get(Customer, customer_payload["customer_id"])
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def _owned_quotation_or_404(db: Session, quotation_id: int, customer: Customer) -> Quotation:
    """A customer token may only touch quotations issued to its own
    organization -- matched by customer_name, since Quotation has no
    customer_id FK (see DATABASE_SCHEMA.md). Without this, any valid
    customer login could read or negotiate on any other customer's deal by
    guessing an id.
    """
    quotation = db.get(Quotation, quotation_id)
    if not quotation or quotation.customer_name != customer.name:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return quotation


@router.post("/portal/signup", response_model=PortalTokenOut)
def portal_signup(payload: CustomerSignupIn, db: Session = Depends(get_db)):
    """Self-service customer signup -- establishes the connection between a
    customer organization and a portal login without needing an internal
    user to create it by hand first. Unlike internal /auth/signup, this
    doesn't require Admin approval: a new company can start negotiating on
    quotes as soon as an internal Sales Rep raises one against their
    customer_name, so gating portal access here would just block that flow.
    Reuses an existing Customer row (matched by name) if the company already
    has one, so a rep's earlier quotation still resolves to the same account.
    A brand-new company always starts at Bronze -- tier is never
    self-selected, it's earned via api.tiering.recalc_customer_tier as the
    account's orders close.
    """
    if db.query(CustomerUser).filter(CustomerUser.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    customer = db.query(Customer).filter(Customer.name == payload.company_name).first()
    if not customer:
        customer = Customer(name=payload.company_name, default_tier="Bronze")
        db.add(customer)
        db.flush()

    cu = CustomerUser(
        customer_id=customer.id, email=payload.email,
        password_hash=hash_password(payload.password), auth_method="password",
    )
    db.add(cu)
    db.commit()
    db.refresh(cu)

    token = create_token({"sub": str(cu.id), "customer_id": cu.customer_id, "type": "customer"})
    return PortalTokenOut(access_token=token, customer_user_id=cu.id, customer_id=cu.customer_id)


@router.post("/portal/login", response_model=PortalTokenOut)
def portal_login(payload: PortalLoginIn, db: Session = Depends(get_db)):
    cu = db.query(CustomerUser).filter(CustomerUser.email == payload.email).first()
    if not cu or not cu.password_hash or not verify_password(payload.password, cu.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token({"sub": str(cu.id), "customer_id": cu.customer_id, "type": "customer"})
    return PortalTokenOut(access_token=token, customer_user_id=cu.id, customer_id=cu.customer_id)


@router.post("/portal/magic-link", response_model=PortalMagicLinkOut)
def request_magic_link(payload: PortalMagicLinkIn, db: Session = Depends(get_db)):
    cu = db.query(CustomerUser).filter(CustomerUser.email == payload.email).first()
    if not cu:
        raise HTTPException(status_code=404, detail="No portal account for this email")
    token = create_token({"sub": str(cu.id), "customer_id": cu.customer_id, "type": "customer"}, expiry_hours=1)
    return PortalMagicLinkOut(magic_link_token=token)


@router.get("/portal/me", response_model=PortalMeOut)
def portal_me(db: Session = Depends(get_db), customer=Depends(get_current_customer_user)):
    cu = db.get(CustomerUser, int(customer["sub"]))
    if not cu:
        raise HTTPException(status_code=404, detail="Portal user not found")
    account = _customer_or_404(db, customer)
    return PortalMeOut(customer_user=cu, customer=account)


@router.get("/portal/quotations", response_model=list[QuotationOut])
def portal_list_quotations(db: Session = Depends(get_db), customer=Depends(get_current_customer_user)):
    account = _customer_or_404(db, customer)
    quotations = db.query(Quotation).filter(Quotation.customer_name == account.name).all()
    for q in quotations:
        _attach_product_names(db, q.lines)
        _attach_margins(db, q)
    return quotations


@router.get("/portal/negotiations", response_model=list[NegotiationRequestOut])
def portal_list_negotiations(db: Session = Depends(get_db), customer=Depends(get_current_customer_user)):
    """Backs the portal 'Messages' screen -- every change request/counter
    this customer's account has ever sent, across all of its quotations,
    newest first.
    """
    account = _customer_or_404(db, customer)
    quotation_ids = [q.id for q in db.query(Quotation.id).filter(Quotation.customer_name == account.name).all()]
    if not quotation_ids:
        return []
    return (
        db.query(NegotiationRequest)
        .filter(NegotiationRequest.quotation_id.in_(quotation_ids))
        .order_by(NegotiationRequest.created_at.desc())
        .all()
    )


@router.get("/portal/quotations/{quotation_id}", response_model=QuotationOut)
def portal_get_quotation(
    quotation_id: int, db: Session = Depends(get_db), customer=Depends(get_current_customer_user)
):
    account = _customer_or_404(db, customer)
    quotation = _owned_quotation_or_404(db, quotation_id, account)
    _attach_product_names(db, quotation.lines)
    _attach_margins(db, quotation)
    return quotation


@router.post("/portal/quotations/{quotation_id}/negotiate", response_model=NegotiationRequestOut)
def submit_negotiation(
    quotation_id: int, payload: NegotiationRequestIn,
    db: Session = Depends(get_db), customer=Depends(get_current_customer_user),
):
    account = _customer_or_404(db, customer)
    quotation = _owned_quotation_or_404(db, quotation_id, account)

    negotiation = NegotiationRequest(
        quotation_id=quotation_id,
        quotation_line_id=payload.quotation_line_id,
        customer_user_id=int(customer["sub"]),
        message=payload.message,
        counter_discount_pct=payload.counter_discount_pct,
        status="pending",
    )
    db.add(negotiation)
    quotation.status = "negotiation"
    db.commit()
    db.refresh(negotiation)
    return negotiation


@router.post("/portal/quotations/{quotation_id}/confirm", response_model=ApprovalOut)
def confirm_quotation(
    quotation_id: int, db: Session = Depends(get_db), customer=Depends(get_current_customer_user)
):
    """PDF B8: "Confirm Quotation" — applies the latest pending counter
    discount (if any) to its line, then re-scores. If the final terms exceed
    approval thresholds, the quotation automatically re-enters the approval
    flow (same score_and_route path as the internal submit endpoint);
    otherwise it's marked confirmed and can move to fulfillment.
    """
    account = _customer_or_404(db, customer)
    quotation = _owned_quotation_or_404(db, quotation_id, account)

    pending = (
        db.query(NegotiationRequest)
        .filter(NegotiationRequest.quotation_id == quotation_id, NegotiationRequest.status == "pending")
        .order_by(NegotiationRequest.created_at.desc())
        .first()
    )
    if pending:
        if pending.counter_discount_pct is not None and pending.quotation_line_id:
            line = db.get(QuotationLine, pending.quotation_line_id)
            if line:
                line.discount_pct = pending.counter_discount_pct
        pending.status = "resolved"

    db.flush()
    approval = score_and_route(db, quotation)
    db.commit()
    db.refresh(approval)
    return approval
