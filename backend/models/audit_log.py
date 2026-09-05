from sqlalchemy import Column, ForeignKey, Integer, JSON, String
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from models.database import Base


class AuditLog(Base):
    """PDF A3 note: "All approvals, rejections, and edits must be logged with
    user, timestamp, and reason." Approval.history already covers approval
    decisions; this table covers everything else (line edits, config
    changes) across any entity.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)  # e.g. "quotation", "discount_tier"
    entity_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # e.g. "edit", "create", "delete"
    reason = Column(String, nullable=True)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
