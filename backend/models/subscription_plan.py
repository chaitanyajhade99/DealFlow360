from sqlalchemy import Column, Integer, JSON, String

from models.database import Base


class SubscriptionPlan(Base):
    """PDF A5: Subscription / Recurring Plan Setup — the reusable plan
    definition (proration + cancellation rules). Distinct from Subscription
    (API_CONTRACT.md), which is a customer's live instance of a plan.
    """

    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g. "Care Plan 2yr"
    cycle = Column(String, nullable=False)  # Monthly / Quarterly / Yearly
    proration_rule = Column(JSON, nullable=False, default=dict)  # mid-cycle qty/plan change rules
    cancellation_rule = Column(JSON, nullable=False, default=dict)  # refund/credit note rules
