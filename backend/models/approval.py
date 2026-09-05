from sqlalchemy import Column, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from models.database import Base


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    blended_risk = Column(String, nullable=False)  # LOW / MEDIUM / HIGH
    stage = Column(String, nullable=False, default="sales_manager")
    assigned_to = Column(String, nullable=True)
    history = Column(JSON, nullable=False, default=list)  # [{user, action, note, at}]
    # Persists score_risk()'s flagged_lines table (screen 6: Line/Discount Given/
    # Limit Allowed/Over By) so it can be re-read later, not just used-and-discarded
    # at submit time. Added in the frontend-integration gap-closure pass.
    flagged_lines = Column(JSON, nullable=False, default=list)

    quotation = relationship("Quotation", back_populates="approvals")
