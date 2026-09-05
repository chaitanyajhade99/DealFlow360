from sqlalchemy import Column, ForeignKey, Integer, JSON, Numeric, String, Boolean
from sqlalchemy.orm import relationship

from models.database import Base


class Product(Base):
    """PDF A2: Product & Price List Management — General Info."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String, unique=True, nullable=False)  # matches product_id strings used on QuotationLine
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # Hardware / Services / Subscription
    price = Column(Numeric(12, 2), nullable=False)
    unit = Column(String, nullable=False, default="each")
    tax_pct = Column(Numeric(5, 2), nullable=False, default=0)
    description = Column(String, nullable=True)
    is_subscription = Column(Boolean, nullable=False, default=False)
    recurring_cycle = Column(String, nullable=True)  # Monthly / Quarterly / Yearly, if is_subscription
    quantity_on_hand = Column(Integer, nullable=True)
    cost = Column(Numeric(12, 2), nullable=True)  # basis for margin calc; not a stored margin, stays correct under price_list overrides
    is_promoted = Column(Boolean, nullable=False, default=False)
    promo_tag = Column(String, nullable=True)

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    price_list_entries = relationship("PriceList", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(Base):
    """PDF A2: Variants — Attribute (e.g. Size/Pack), Values, Extra prices."""

    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    attribute = Column(String, nullable=False)  # e.g. "Color", "RAM"
    value = Column(String, nullable=False)  # e.g. "Blue", "16GB"
    extra_price = Column(Numeric(12, 2), nullable=False, default=0)

    product = relationship("Product", back_populates="variants")


class PriceList(Base):
    """PDF A2: Price Lists — customer tier based pricing, currency specific rules."""

    __tablename__ = "price_lists"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_tier = Column(String, nullable=False)  # Bronze / Silver / Gold
    currency = Column(String, nullable=False, default="USD")
    price_rule = Column(JSON, nullable=False, default=dict)  # e.g. {"type": "fixed", "price": 1080} or {"type": "markup_pct", "value": 10}

    product = relationship("Product", back_populates="price_list_entries")
