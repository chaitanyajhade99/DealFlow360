from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric

from models.database import Base


class UpsellRule(Base):
    """PDF A6 (optional): Upsell / Cross Sell Rule Setup."""

    __tablename__ = "upsell_rules"

    id = Column(Integer, primary_key=True, index=True)
    source_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    suggested_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    is_promoted = Column(Boolean, nullable=False, default=False)
    min_margin_pct = Column(Numeric(5, 2), nullable=False, default=0)
