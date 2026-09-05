from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from models.database import Base


class Customer(Base):
    """A customer organization (PDF section 3, role: Customer Portal User).

    Not FK-linked from Quotation yet — Quotation.customer_name/customer_tier
    (per API_CONTRACT.md) stay free-text/snapshot fields to avoid an ALTER on
    the already-deployed quotations table. Join by matching customer_name to
    Customer.name when a link is needed; a real FK is a follow-up contract
    change once the team agrees on it.
    """

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    default_tier = Column(String, nullable=False)  # Bronze / Silver / Gold
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # pending / approved / rejected. A customer created by an internal user
    # (POST /customers, or the quotation builder's "add new customer") is
    # auto-"approved" via the column default -- an employee already vetted
    # it. A customer created via self-service /portal/signup starts
    # "pending": it can't log in, and GET /customers (the quotation
    # builder's customer picker) only lists "approved" ones, so a
    # newly-signed-up company doesn't show up anywhere until an Admin
    # approves it (see api.admin_customers).
    status = Column(String, nullable=False, server_default="approved")

    portal_users = relationship("CustomerUser", back_populates="customer", cascade="all, delete-orphan")


class CustomerUser(Base):
    """Portal login for a customer contact (PDF A1: "magic link, or email and
    password"). This is what the separate, restricted customer-facing
    negotiation screen (B8) authenticates against.
    """

    __tablename__ = "customer_users"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)  # null when auth_method is magic_link
    auth_method = Column(String, nullable=False, default="password")  # password / magic_link
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="portal_users")
