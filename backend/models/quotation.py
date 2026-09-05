from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Date, DateTime

from models.database import Base


class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_tier = Column(String, nullable=False)  # Bronze / Silver / Gold
    status = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sales_rep_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expected_delivery_date = Column(Date, nullable=True)  # backs B9 delivery slippage indicator
    actual_delivery_date = Column(Date, nullable=True)

    lines = relationship(
        "QuotationLine", back_populates="quotation", cascade="all, delete-orphan"
    )
    approvals = relationship(
        "Approval", back_populates="quotation", cascade="all, delete-orphan"
    )
    fulfillment_splits = relationship(
        "FulfillmentSplit", back_populates="quotation", cascade="all, delete-orphan"
    )
    invoices = relationship(
        "Invoice", back_populates="quotation", cascade="all, delete-orphan"
    )


class QuotationLine(Base):
    __tablename__ = "quotation_lines"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    product_id = Column(String, nullable=False)
    category = Column(String, nullable=False)  # Hardware / Services / Subscription
    qty = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount_pct = Column(Numeric(5, 2), nullable=False, default=0)
    category_limit_pct = Column(Numeric(5, 2), nullable=False)

    quotation = relationship("Quotation", back_populates="lines")
