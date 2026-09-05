from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.types import Date

from models.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    plan = Column(String, nullable=False)
    cycle = Column(String, nullable=False)  # Monthly / Quarterly / Yearly
    next_bill_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default="active")
    # Added for the frontend-integration gap-closure pass so PDF B7's mid-cycle
    # proration and cancellation refunds can be computed for real instead of
    # requiring the caller to supply a manually-guessed number.
    amount = Column(Numeric(12, 2), nullable=True)
    qty = Column(Integer, nullable=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=True)
