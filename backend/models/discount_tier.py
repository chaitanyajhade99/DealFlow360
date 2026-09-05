from sqlalchemy import Column, Integer, JSON, Numeric, String

from models.database import Base


class DiscountTier(Base):
    """Backend config entity (PDF section A3 / wireframe screen 18:
    "Discount tiers and approval chains"). Combines tier ceiling, per-category
    ceilings, and the approval-chain routing rule into one row per tier so a
    single table covers the whole config screen.
    """

    __tablename__ = "discount_tiers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Bronze / Silver / Gold
    max_discount_pct = Column(Numeric(5, 2), nullable=False)  # overall tier ceiling

    # {"Hardware": 15, "Services": 10, "Subscription": 10}
    category_limits = Column(JSON, nullable=False, default=dict)

    # Blended-risk -> required approval stage, e.g.
    # {"LOW": "none", "MEDIUM": "sales_manager", "HIGH": "sales_manager_then_finance"}
    approval_chain = Column(JSON, nullable=False, default=dict)
