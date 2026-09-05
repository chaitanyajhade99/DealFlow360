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

    quotation = relationship("Quotation", back_populates="approvals")
