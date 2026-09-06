from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import Invoice, Payment, Product, Quotation, Subscription, get_db
from api.deps import require_roles
from api.tiering import recalc_customer_tier
from api.schemas import InvoiceCreate, InvoiceOut, PaymentIn, PaymentOut

router = APIRouter(tags=["invoices"])

# PDF A5/B7: "monthly, quarterly, yearly" -- kept identical to
# api.subscriptions.CYCLE_DAYS (not imported from there to avoid a
# cross-router import cycle; both are fixed day-counts, the standard
# simplification for proration/scheduling without a real billing calendar).
_CYCLE_DAYS = {"Monthly": 30, "Quarterly": 90, "Yearly": 365}


def _create_subscriptions_if_needed(db: Session, quotation: Quotation) -> None:
    """PDF B7: "Order may include recurring subscription lines, which
    generate a billing schedule alongside any one time invoice." This was
    previously entirely disconnected -- a Subscription row only ever existed
    if someone hand-called POST /subscriptions; nothing in the actual
    quote-to-cash flow created one. Runs on every confirm/approve path
    (mirrors create_invoice_if_needed's call sites) and is idempotent per
    line, matched on (quotation_id, plan=product_id), so re-scoring the same
    quotation (e.g. after a negotiation counter) never creates duplicates.
    """
    subscription_lines = [l for l in quotation.lines if l.category == "Subscription"]
    if not subscription_lines:
        return

    existing_plans = {
        s.plan
        for s in db.query(Subscription).filter(Subscription.quotation_id == quotation.id).all()
    }
    products_by_code = {
        p.product_code: p
        for p in db.query(Product).filter(Product.product_code.in_([l.product_id for l in subscription_lines])).all()
    }

    for line in subscription_lines:
        if line.product_id in existing_plans:
            continue
        product = products_by_code.get(line.product_id)
        cycle = (product.recurring_cycle if product else None) or "Monthly"
        net_amount = round(float(line.unit_price) * (1 - float(line.discount_pct) / 100) * line.qty, 2)
        db.add(Subscription(
            customer_name=quotation.customer_name,
            plan=line.product_id,
            cycle=cycle,
            next_bill_date=date.today() + timedelta(days=_CYCLE_DAYS.get(cycle, 30)),
            status="active",
            amount=net_amount,
            qty=line.qty,
            quotation_id=quotation.id,
        ))
    db.flush()


def create_invoice_if_needed(db: Session, quotation: Quotation) -> Invoice | None:
    """Auto-generate an invoice once a quotation is fully confirmed (PDF:
    "Once confirmed, the order proceeds to fulfillment and billing"). Called
    from score_and_route (no-approval-needed path) and from the approval
    decision endpoint (full chain cleared). Idempotent — one invoice per
    quotation.

    Recurring (Subscription-category) lines are billed on their own cycle,
    not folded into this one-time invoice (PDF B7: "Shows one time lines and
    recurring lines separately") -- see _create_subscriptions_if_needed,
    called unconditionally below since a pure-subscription order can have a
    zero one-time total and still need its recurring schedule created.
    """
    _create_subscriptions_if_needed(db, quotation)

    existing = db.query(Invoice).filter(Invoice.quotation_id == quotation.id).first()
    if existing:
        return existing

    total = sum(
        float(line.unit_price) * line.qty * (1 - float(line.discount_pct) / 100)
        for line in quotation.lines
        if line.category != "Subscription"
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
def create_invoice(
    payload: InvoiceCreate, db: Session = Depends(get_db),
    _finance=Depends(require_roles("finance", "admin")),
):
    quotation = db.get(Quotation, payload.quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    invoice = Invoice(**payload.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


# PDF section 3 gives billing/invoice records to Finance/Operations
# ("Reconciles recurring billing and credit notes") -- a Sales Rep or Sales
# Manager has no stated responsibility over raw invoice/payment records, so
# reads are gated the same as the mutations below, not left open just
# because nothing forced the question.
_CAN_READ_INVOICES = require_roles("finance", "admin")


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db), _=Depends(_CAN_READ_INVOICES)):
    return db.query(Invoice).all()


@router.get("/invoices/{id}", response_model=InvoiceOut)
def get_invoice(id: int, db: Session = Depends(get_db), _=Depends(_CAN_READ_INVOICES)):
    invoice = db.get(Invoice, id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{id}/pay", response_model=PaymentOut)
def record_payment(
    id: int, payload: PaymentIn, db: Session = Depends(get_db),
    _finance=Depends(require_roles("finance", "admin")),
):
    """Finance-only MANUAL reconciliation (e.g. an offline bank transfer the
    customer already made outside DealFlow360) -- not the real payment path.
    The actual online payment is customer-initiated via Razorpay Checkout
    through the portal (see api/portal.py's razorpay-order/verify routes);
    this endpoint exists only so Finance can mark an invoice paid when money
    genuinely arrived some other way, and the frontend gates it behind an
    explicit confirmation + reference note so it can't be mistaken for a
    real payment.
    """
    # SELECT ... FOR UPDATE: without this, two concurrent requests (a
    # double-click, or two Finance users reconciling the same invoice at
    # once) can both read status="unpaid" before either commits, and both
    # insert a Payment. Locking the row for the duration of this
    # transaction makes the second request block until the first commits,
    # so it then sees the real post-payment state.
    invoice = db.query(Invoice).filter(Invoice.id == id).with_for_update().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="This invoice is already paid")
    if float(payload.amount) <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")

    prior_paid = sum(float(p.amount) for p in db.query(Payment).filter(Payment.invoice_id == id).all())
    remaining = round(float(invoice.amount) - prior_paid, 2)
    if float(payload.amount) > remaining + 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Payment of {payload.amount} exceeds the remaining balance of {remaining}",
        )

    payment = Payment(invoice_id=id, amount=payload.amount, method=payload.method)
    db.add(payment)

    if prior_paid + float(payload.amount) >= float(invoice.amount) - 0.01:
        invoice.status = "paid"

    db.commit()
    db.refresh(payment)
    return payment
