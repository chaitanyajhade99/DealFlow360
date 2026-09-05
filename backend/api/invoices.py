import hashlib
import hmac
import os
from datetime import date, timedelta

import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import Invoice, Payment, Quotation, get_db
from api.tiering import recalc_customer_tier
from api.schemas import (
    InvoiceCreate, InvoiceOut, PaymentIn, PaymentOut,
    RazorpayOrderOut, RazorpayVerifyIn,
)

router = APIRouter(tags=["invoices"])

# Razorpay TEST-mode credentials. Overridable via env vars for real
# deployments; the defaults below are the test key pair provided for this
# hackathon build so checkout works out of the box in dev.
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_TYRBlT6eTZOuNQ")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "9enh7cNbIqwuX33A1v0zAnkz")

_razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_invoice_if_needed(db: Session, quotation: Quotation) -> Invoice | None:
    """Auto-generate an invoice once a quotation is fully confirmed (PDF:
    "Once confirmed, the order proceeds to fulfillment and billing"). Called
    from score_and_route (no-approval-needed path) and from the approval
    decision endpoint (full chain cleared). Idempotent — one invoice per
    quotation.
    """
    existing = db.query(Invoice).filter(Invoice.quotation_id == quotation.id).first()
    if existing:
        return existing

    total = sum(
        float(line.unit_price) * line.qty * (1 - float(line.discount_pct) / 100)
        for line in quotation.lines
    )
    if total <= 0:
        return None

    invoice = Invoice(
        quotation_id=quotation.id, amount=round(total, 2),
        status="unpaid", due_date=date.today() + timedelta(days=30),
    )
    db.add(invoice)
    db.flush()

    # A confirmed order is what "earns" tier progress -- recalculate now
    # rather than waiting for a separate job, so the very next quotation
    # this customer gets already reflects their new tier/discount ceiling.
    recalc_customer_tier(db, quotation.customer_name)
    return invoice


@router.post("/invoices", response_model=InvoiceOut)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    quotation = db.get(Quotation, payload.quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    invoice = Invoice(**payload.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).all()


@router.get("/invoices/{id}", response_model=InvoiceOut)
def get_invoice(id: int, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{id}/pay", response_model=PaymentOut)
def record_payment(id: int, payload: PaymentIn, db: Session = Depends(get_db)):
    """Quick Test Flow step 8: record a payment, invoice status updates."""
    invoice = db.get(Invoice, id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    prior_paid = sum(float(p.amount) for p in db.query(Payment).filter(Payment.invoice_id == id).all())
    payment = Payment(invoice_id=id, amount=payload.amount, method=payload.method)
    db.add(payment)

    if prior_paid + float(payload.amount) >= float(invoice.amount):
        invoice.status = "paid"

    db.commit()
    db.refresh(payment)
    return payment


@router.post("/invoices/{id}/razorpay-order", response_model=RazorpayOrderOut)
def create_razorpay_order(id: int, db: Session = Depends(get_db)):
    """Step 1 of the Razorpay Checkout flow: create an order server-side so
    the amount can't be tampered with client-side, then hand the order id +
    publishable key to the frontend to open Checkout.
    """
    invoice = db.get(Invoice, id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    amount_paise = int(round(float(invoice.amount) * 100))
    order = _razorpay_client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"invoice-{invoice.id}",
        "notes": {"invoice_id": str(invoice.id), "quotation_id": str(invoice.quotation_id)},
    })
    return RazorpayOrderOut(
        order_id=order["id"], amount=amount_paise, currency="INR",
        key_id=RAZORPAY_KEY_ID, invoice_id=invoice.id,
    )


@router.post("/invoices/{id}/razorpay-verify", response_model=PaymentOut)
def verify_razorpay_payment(id: int, payload: RazorpayVerifyIn, db: Session = Depends(get_db)):
    """Step 2: verify Checkout's signature server-side (HMAC-SHA256 of
    order_id|payment_id, keyed with the account secret) before ever trusting
    that a payment succeeded -- Razorpay's own recommended flow, since the
    client-side "success" callback alone is not proof of payment.
    """
    invoice = db.get(Invoice, id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    payment = Payment(invoice_id=id, amount=invoice.amount, method="razorpay")
    db.add(payment)
    invoice.status = "paid"
    db.commit()
    db.refresh(payment)
    return payment
