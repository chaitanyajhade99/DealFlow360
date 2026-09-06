"""Customer-facing portal (PDF B8) — separate, restricted from the internal
workspace per section 7's Technical Guidelines. Every route here requires a
customer-type JWT (get_current_customer_user), never an internal one.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Customer, CustomerUser, Invoice, NegotiationRequest, Payment, Quotation, QuotationLine, get_db
from api import payments
from api.auth_utils import create_token, hash_password, verify_password
from api.deps import get_current_customer_user
from api.quotations import _attach_margins, _attach_product_names, build_quotation_pdf, score_and_route
from api.schemas import (
    ApprovalOut,
    CustomerOut,
    CustomerSignupIn,
    CustomerUserOut,
    InvoiceOut,
    NegotiationRequestIn,
    NegotiationRequestOut,
    PaymentOut,
    PortalLoginIn,
    PortalMagicLinkIn,
    PortalMagicLinkOut,
    PortalMeOut,
    PortalSignupOut,
    PortalTokenOut,
    QuotationOut,
    RazorpayOrderOut,
    RazorpayVerifyIn,
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


def _owned_invoice_or_404(db: Session, invoice_id: int, customer: Customer) -> Invoice:
    """Same ownership rule as quotations: an invoice belongs to whichever
    quotation it was raised for, so match through that.
    """
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    quotation = db.get(Quotation, invoice.quotation_id)
    if not quotation or quotation.customer_name != customer.name:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/portal/signup", response_model=PortalSignupOut)
def portal_signup(payload: CustomerSignupIn, db: Session = Depends(get_db)):
    """Self-service customer signup -- establishes the connection between a
    customer organization and a portal login without needing an internal
    user to create it by hand first.

    A brand-new company starts life as a "pending" Customer (see
    models.Customer.status) and does NOT get a usable token here -- an
    Admin must approve it (POST /admin/customers/{id}/approve) before this
    account can log in, exactly like internal /auth/signup. Signing up as an
    additional contact for a company that's already approved skips the
    wait -- the org itself was already vetted, only the very first contact
    needs Admin review. Reuses an existing Customer row (matched by name) if
    the company already has one, so a rep's earlier quotation still resolves
    to the same account. A brand-new company always starts at Bronze -- tier
    is never self-selected, it's earned via api.tiering.recalc_customer_tier
    as the account's orders close.
    """
    if db.query(CustomerUser).filter(func.lower(CustomerUser.email) == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    customer = db.query(Customer).filter(func.lower(Customer.name) == payload.company_name.lower()).first()
    if not customer:
        customer = Customer(name=payload.company_name, default_tier="Bronze", status="pending")
        db.add(customer)
        db.flush()

    cu = CustomerUser(
        customer_id=customer.id, email=payload.email,
        password_hash=hash_password(payload.password), auth_method="password",
    )
    db.add(cu)
    db.commit()
    db.refresh(cu)

    if customer.status != "approved":
        return PortalSignupOut(status="pending", customer_user_id=cu.id, customer_id=cu.customer_id)

    token = create_token({"sub": str(cu.id), "customer_id": cu.customer_id, "type": "customer"})
    return PortalSignupOut(
        status="approved", customer_user_id=cu.id, customer_id=cu.customer_id, access_token=token,
    )


@router.post("/portal/login", response_model=PortalTokenOut)
def portal_login(payload: PortalLoginIn, db: Session = Depends(get_db)):
    cu = db.query(CustomerUser).filter(func.lower(CustomerUser.email) == payload.email.lower()).first()
    if not cu or not cu.password_hash or not verify_password(payload.password, cu.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    customer = db.get(Customer, cu.customer_id)
    if not customer or customer.status == "pending":
        raise HTTPException(status_code=403, detail="Your account is awaiting admin approval.")
    if customer.status == "rejected":
        raise HTTPException(status_code=403, detail="Your account request was rejected. Contact us for help.")
    token = create_token({"sub": str(cu.id), "customer_id": cu.customer_id, "type": "customer"})
    return PortalTokenOut(access_token=token, customer_user_id=cu.id, customer_id=cu.customer_id)


@router.post("/portal/magic-link", response_model=PortalMagicLinkOut)
def request_magic_link(payload: PortalMagicLinkIn, db: Session = Depends(get_db)):
    cu = db.query(CustomerUser).filter(func.lower(CustomerUser.email) == payload.email.lower()).first()
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


@router.get("/portal/quotations/{quotation_id}/pdf")
def portal_quotation_pdf(
    quotation_id: int, db: Session = Depends(get_db), customer=Depends(get_current_customer_user)
):
    """Customer-facing PDF preview/download of their own quotation --
    ownership-checked exactly like every other /portal/* route. Reuses the
    same builder as the internal export but with include_governance=False:
    internal risk scoring and reviewer notes stay workspace-only.
    """
    account = _customer_or_404(db, customer)
    quotation = _owned_quotation_or_404(db, quotation_id, account)
    return build_quotation_pdf(db, quotation, preview=True, include_governance=False)


@router.post("/portal/quotations/{quotation_id}/negotiate", response_model=NegotiationRequestOut)
def submit_negotiation(
    quotation_id: int, payload: NegotiationRequestIn,
    db: Session = Depends(get_db), customer=Depends(get_current_customer_user),
):
    account = _customer_or_404(db, customer)
    quotation = _owned_quotation_or_404(db, quotation_id, account)

    if payload.counter_discount_pct is not None:
        # A "counter" that isn't actually higher than what's already on the
        # quote isn't a counter-offer -- enforced here too, not just in the
        # UI, since this endpoint takes a customer JWT directly and nothing
        # else stops a scripted request from sending a lower/equal value.
        line = db.get(QuotationLine, payload.quotation_line_id) if payload.quotation_line_id else None
        if line and line.quotation_id == quotation_id and float(payload.counter_discount_pct) <= float(line.discount_pct):
            raise HTTPException(
                status_code=400,
                detail=f"Counter discount must be higher than the current {line.discount_pct}% on this line.",
            )
        if float(payload.counter_discount_pct) > 100:
            raise HTTPException(status_code=400, detail="Counter discount cannot exceed 100%.")

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


@router.get("/portal/invoices", response_model=list[InvoiceOut])
def portal_list_invoices(db: Session = Depends(get_db), customer=Depends(get_current_customer_user)):
    """Every invoice raised against this account's own quotations -- backs
    a "Billing" screen in the portal so the customer can see what's owed
    and pay it themselves (see the razorpay-order/verify routes below).
    """
    account = _customer_or_404(db, customer)
    quotation_ids = [q.id for q in db.query(Quotation.id).filter(Quotation.customer_name == account.name).all()]
    if not quotation_ids:
        return []
    return db.query(Invoice).filter(Invoice.quotation_id.in_(quotation_ids)).order_by(Invoice.id.desc()).all()


@router.get("/portal/invoices/{invoice_id}", response_model=InvoiceOut)
def portal_get_invoice(invoice_id: int, db: Session = Depends(get_db), customer=Depends(get_current_customer_user)):
    account = _customer_or_404(db, customer)
    return _owned_invoice_or_404(db, invoice_id, account)


@router.post("/portal/invoices/{invoice_id}/razorpay-order", response_model=RazorpayOrderOut)
def portal_create_razorpay_order(
    invoice_id: int, db: Session = Depends(get_db), customer=Depends(get_current_customer_user)
):
    """Business rule: the customer pays their own invoice -- this route (and
    verify, below) is the ONLY way an invoice gets paid through a real
    payment gateway. It is customer-JWT-only and ownership-checked, exactly
    like every other /portal/* route; the internal workspace can no longer
    trigger a Razorpay charge on a customer's behalf (see api/invoices.py).
    """
    account = _customer_or_404(db, customer)
    invoice = _owned_invoice_or_404(db, invoice_id, account)
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")
    order = payments.create_order(invoice.id, invoice.amount, invoice.quotation_id)
    return RazorpayOrderOut(**order, invoice_id=invoice.id)


@router.post("/portal/invoices/{invoice_id}/razorpay-verify", response_model=PaymentOut)
def portal_verify_razorpay_payment(
    invoice_id: int, payload: RazorpayVerifyIn,
    db: Session = Depends(get_db), customer=Depends(get_current_customer_user),
):
    account = _customer_or_404(db, customer)
    invoice = _owned_invoice_or_404(db, invoice_id, account)

    if not payments.verify_signature(payload.razorpay_order_id, payload.razorpay_payment_id, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    # Row lock + already-paid guard: without this, a double-click on "Pay
    # Now" (which creates two Razorpay orders before either verifies, since
    # portal_create_razorpay_order's own already-paid check only runs at
    # order-creation time) could verify twice and insert two Payment rows
    # against the same invoice. Same race-safety approach as the internal
    # Finance reconciliation endpoint (api/invoices.py::record_payment).
    invoice = db.query(Invoice).filter(Invoice.id == invoice.id).with_for_update().first()
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="This invoice is already paid")

    payment = Payment(invoice_id=invoice.id, amount=invoice.amount, method="razorpay")
    db.add(payment)
    invoice.status = "paid"
    db.commit()
    db.refresh(payment)
    return payment
