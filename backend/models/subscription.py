from sqlalchemy import Column, Integer, String
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
