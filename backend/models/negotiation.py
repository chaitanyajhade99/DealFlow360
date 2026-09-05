from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from models.database import Base


class NegotiationRequest(Base):
    """PDF B8: Customer Portal Negotiation Screen — "Line level comment and
    change request tool" + "Counter discount proposal field" + Submit
    Request button.
    """

    __tablename__ = "negotiation_requests"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    quotation_line_id = Column(Integer, ForeignKey("quotation_lines.id"), nullable=True)
    customer_user_id = Column(Integer, ForeignKey("customer_users.id"), nullable=True)
    message = Column(String, nullable=True)
    counter_discount_pct = Column(Numeric(5, 2), nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending / resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
