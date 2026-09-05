"""Customer-facing portal (PDF B8) — separate, restricted from the internal
workspace per section 7's Technical Guidelines. Every route here requires a
customer-type JWT (get_current_customer_user), never an internal one.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import CustomerUser, NegotiationRequest, Quotation, QuotationLine, get_db
from api.auth_utils import create_token, verify_password
from api.deps import get_current_customer_user
from api.quotations import _attach_margins, _attach_product_names, score_and_route
from api.schemas import (
    ApprovalOut,
    NegotiationRequestIn,
    NegotiationRequestOut,
    PortalLoginIn,
    PortalMagicLinkIn,
    PortalMagicLinkOut,
    PortalTokenOut,
    QuotationOut,
)

router = APIRouter(tags=["customer-portal"])


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


@router.get("/portal/quotations/{quotation_id}", response_model=QuotationOut)
def portal_get_quotation(
    quotation_id: int, db: Session = Depends(get_db), customer=Depends(get_current_customer_user)
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    _attach_product_names(db, quotation.lines)
    _attach_margins(db, quotation)
    return quotation


@router.post("/portal/quotations/{quotation_id}/negotiate", response_model=NegotiationRequestOut)
def submit_negotiation(
    quotation_id: int, payload: NegotiationRequestIn,
    db: Session = Depends(get_db), customer=Depends(get_current_customer_user),
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

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
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

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
