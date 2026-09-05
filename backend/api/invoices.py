from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import Invoice, Payment, Quotation, get_db
from api.tiering import recalc_customer_tier
from api.schemas import InvoiceCreate, InvoiceOut, PaymentIn, PaymentOut

router = APIRouter(tags=["invoices"])


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
    """Finance-only MANUAL reconciliation (e.g. an offline bank transfer the
    customer already made outside DealFlow360) -- not the real payment path.
    The actual online payment is customer-initiated via Razorpay Checkout
    through the portal (see api/portal.py's razorpay-order/verify routes);
    this endpoint exists only so Finance can mark an invoice paid when money
    genuinely arrived some other way, and the frontend gates it behind an
    explicit confirmation + reference note so it can't be mistaken for a
    real payment.
    """
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
