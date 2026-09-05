"""Pydantic request/response schemas for the API layer."""
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ---- Quotation ----

class QuotationLineIn(BaseModel):
    product_id: str
    category: str
    qty: int
    unit_price: float
    discount_pct: float = 0
    # Optional: auto-filled from the quotation's DiscountTier.category_limits
    # (by category) when omitted. Pass explicitly to override.
    category_limit_pct: Optional[float] = None


class QuotationLineOut(QuotationLineIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quotation_id: int
    # Cosmetic join, not a DB column on quotation_lines — see api/quotations.py::_attach_product_names
    product_name: Optional[str] = None
    # Transient, computed from Product.cost — see api/quotations.py::_attach_margins
    margin: Optional[float] = None


class QuotationCreate(BaseModel):
    customer_name: str
    customer_tier: str
    sales_rep_id: Optional[int] = None
    expected_delivery_date: Optional[date] = None
    lines: list[QuotationLineIn] = []


class QuotationLinesUpdate(BaseModel):
    lines: list[QuotationLineIn]
    edited_by_user_id: Optional[int] = None
    reason: Optional[str] = None


class QuotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_name: str
    customer_tier: str
    status: str
    created_at: datetime
    sales_rep_id: Optional[int] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    lines: list[QuotationLineOut] = []
    # Transient, sum of line margins — see api/quotations.py::_attach_margins
    total_margin: Optional[float] = None


# ---- Approval ----

class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quotation_id: int
    blended_risk: str
    stage: str
    assigned_to: Optional[str] = None
    history: list[dict[str, Any]] = []


class ApprovalDecisionIn(BaseModel):
    action: str  # approve | reject | return
    user: str
    note: Optional[str] = None


# ---- Fulfillment ----

class FulfillmentSplitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quotation_id: int
    splits: list[dict[str, Any]] = []
    # Transient, not persisted to fulfillment_splits.splits — see api/fulfillment.py
    backorders: list[dict[str, Any]] = []


# ---- Subscription ----

class SubscriptionCreate(BaseModel):
    customer_name: str
    plan: str
    cycle: str
    next_bill_date: Optional[date] = None
    status: str = "active"


class SubscriptionOut(SubscriptionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---- Invoice / Payment ----

class InvoiceCreate(BaseModel):
    quotation_id: int
    amount: float
    due_date: Optional[date] = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quotation_id: int
    amount: float
    status: str
    due_date: Optional[date] = None


class PaymentIn(BaseModel):
    amount: float
    method: str = "manual"


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    amount: float
    method: str
    paid_at: datetime


# ---- Deal health ----

class DealHealthOut(BaseModel):
    stalled_deals: list[dict[str, Any]]
    discount_anomalies: list[dict[str, Any]]
    delivery_slippage: list[dict[str, Any]] = []


# ---- Discount Tier ----

class DiscountTierIn(BaseModel):
    name: str
    max_discount_pct: float
    category_limits: dict[str, float] = {}
    approval_chain: dict[str, str] = {}


class DiscountTierOut(DiscountTierIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---- Auth (internal users) ----

class UserSignupIn(BaseModel):
    name: str
    email: str
    password: str
    role: str  # sales_rep / sales_manager / finance / admin
    seniority: Optional[int] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    seniority: Optional[int] = None
    created_at: datetime


class UserLoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- Customer portal auth ----

class PortalLoginIn(BaseModel):
    email: str
    password: str


class PortalTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_user_id: int
    customer_id: int


class PortalMagicLinkIn(BaseModel):
    email: str


class PortalMagicLinkOut(BaseModel):
    # No email service is wired up — normally this token would be emailed,
    # not returned directly. Returned here so the flow is testable end-to-end.
    magic_link_token: str


# ---- Negotiation (customer portal) ----

class NegotiationRequestIn(BaseModel):
    message: Optional[str] = None
    counter_discount_pct: Optional[float] = None
    quotation_line_id: Optional[int] = None


class NegotiationRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quotation_id: int
    quotation_line_id: Optional[int] = None
    customer_user_id: Optional[int] = None
    message: Optional[str] = None
    counter_discount_pct: Optional[float] = None
    status: str
    created_at: datetime


# ---- Warehouse ----

class WarehouseIn(BaseModel):
    name: str
    stock: list[dict[str, Any]] = []
    shipping_cost_per_unit: float = 0
    shipment_fixed_cost: float = 0


class WarehouseOut(WarehouseIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---- Product ----

class ProductVariantIn(BaseModel):
    attribute: str
    value: str
    extra_price: float = 0


class ProductVariantOut(ProductVariantIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int


class PriceListIn(BaseModel):
    customer_tier: str
    currency: str = "USD"
    price_rule: dict[str, Any] = {}


class PriceListOut(PriceListIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int


class ProductIn(BaseModel):
    product_code: str
    name: str
    category: str
    price: float
    unit: str = "each"
    tax_pct: float = 0
    description: Optional[str] = None
    is_subscription: bool = False
    recurring_cycle: Optional[str] = None
    quantity_on_hand: Optional[int] = None
    cost: Optional[float] = None
    is_promoted: bool = False
    promo_tag: Optional[str] = None
    variants: list[ProductVariantIn] = []
    price_lists: list[PriceListIn] = []


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_code: str
    name: str
    category: str
    price: float
    unit: str
    tax_pct: float
    description: Optional[str] = None
    is_subscription: bool
    recurring_cycle: Optional[str] = None
    quantity_on_hand: Optional[int] = None
    cost: Optional[float] = None
    is_promoted: bool
    promo_tag: Optional[str] = None
    variants: list[ProductVariantOut] = []
    price_list_entries: list[PriceListOut] = []


# ---- Subscription plans + subscription lifecycle ----

class SubscriptionPlanIn(BaseModel):
    name: str
    cycle: str
    proration_rule: dict[str, Any] = {}
    cancellation_rule: dict[str, Any] = {}


class SubscriptionPlanOut(SubscriptionPlanIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SubscriptionUpdate(BaseModel):
    plan: Optional[str] = None
    cycle: Optional[str] = None
    next_bill_date: Optional[date] = None
    status: Optional[str] = None


class SubscriptionCancelIn(BaseModel):
    reason: Optional[str] = None
    refund_amount: Optional[float] = None  # rep/finance-supplied; Subscription has no amount field to prorate from


class CreditNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subscription_id: Optional[int] = None
    invoice_id: Optional[int] = None
    amount: float
    reason: Optional[str] = None
    created_at: datetime


# ---- Reporting ----

class ReportSummaryOut(BaseModel):
    quotes_created: int
    avg_approval_time_hours: Optional[float] = None
    top_discounted_product: Optional[str] = None
    matching_quotations: list[dict[str, Any]]
