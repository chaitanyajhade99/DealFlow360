"""Customer tier is earned, not chosen. A portal signup always starts at
Bronze; this recalculates a customer's tier from how many of its quotations
have actually closed (confirmed/approved), so a customer who orders more
often automatically earns a higher tier -- and, via DiscountTier, a higher
discount ceiling. Called whenever a quotation for that customer reaches a
closed state (see api/invoices.py::create_invoice_if_needed).
"""
from sqlalchemy.orm import Session

from models import Customer, Quotation

CLOSED_STATUSES = ("confirmed", "approved")

# order_count >= threshold -> tier. Checked highest-first.
TIER_THRESHOLDS = [
    (7, "Gold"),
    (3, "Silver"),
    (0, "Bronze"),
]


def tier_for_order_count(order_count: int) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if order_count >= threshold:
            return tier
    return "Bronze"


def recalc_customer_tier(db: Session, customer_name: str) -> None:
    customer = db.query(Customer).filter(Customer.name == customer_name).first()
    if not customer:
        return
    order_count = (
        db.query(Quotation)
        .filter(Quotation.customer_name == customer_name, Quotation.status.in_(CLOSED_STATUSES))
        .count()
    )
    new_tier = tier_for_order_count(order_count)
    if customer.default_tier != new_tier:
        customer.default_tier = new_tier
