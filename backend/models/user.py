from sqlalchemy import Column, Integer, SmallInteger, String
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from models.database import Base


class User(Base):
    """Internal users (PDF section 3): Sales Rep, Sales Manager/Approver,
    Finance/Operations User, Admin. Customer portal users are a separate
    entity (CustomerUser) since the portal is a restricted, separate view.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # sales_rep / sales_manager / finance / admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    seniority = Column(SmallInteger, nullable=True)  # 0 junior, 1 mid, 2 principal (sales_rep only)
    # pending / approved / rejected. Self-service /auth/signup creates
    # "pending" accounts that cannot log in until an Admin approves them
    # (POST /admin/users/{id}/approve) -- seeded/admin-created users default
    # to "approved" via the column's server_default so existing rows/logins
    # are unaffected.
    status = Column(String, nullable=False, server_default="approved")
