from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import relationship

from models.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    stock = Column(JSON, nullable=False, default=list)  # [{product_id, qty}]
    shipping_cost_per_unit = Column(Numeric(10, 2), nullable=False, default=0)
    shipment_fixed_cost = Column(Numeric(10, 2), nullable=False, default=0)
    # PDF A4: "configure stock levels and replenishment rules per warehouse".
    # Free-form json (e.g. {"reorder_point": 10, "reorder_qty": 50}) since the
    # PDF doesn't pin down a fixed shape.
    replenishment_rules = Column(JSON, nullable=False, default=dict)


class FulfillmentSplit(Base):
    __tablename__ = "fulfillment_splits"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    splits = Column(JSON, nullable=False, default=list)  # [{warehouse_id, product_id, qty, cost}]
    # PDF B6: "Manual Override" button. When true, GET /fulfillment/{id} stops
    # recomputing/overwriting splits from the live auto-allocation engine on
    # every call -- the rep's persisted choice is authoritative until they
    # explicitly reset it back to the suggested split.
    is_manual_override = Column(Boolean, nullable=False, default=False, server_default="false")

    quotation = relationship("Quotation", back_populates="fulfillment_splits")
