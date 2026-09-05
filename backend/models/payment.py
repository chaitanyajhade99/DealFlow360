from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from models.database import Base


class Payment(Base):
    """Quick Test Flow step 8: "confirm the order, record a payment, and
    check that the invoice status updates correctly." No table existed for
    this yet — Invoice.status was write-only from nowhere.
    """

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(String, nullable=False, default="manual")  # card / bank_transfer / manual
    paid_at = Column(DateTime(timezone=True), server_default=func.now())


class CreditNote(Base):
    """PDF B7: "automatic partial refund or credit note trigger" on
    subscription cancel/modify.
    """

    __tablename__ = "credit_notes"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
