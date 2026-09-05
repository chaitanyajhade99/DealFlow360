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
    flagged_lines: list[dict[str, Any]] = []


class ApprovalDecisionIn(BaseModel):
    action: str  # approve | reject | return
    user: str
    note: Optional[str] = None
    user_id: Optional[int] = None  # optional, for AuditLog attribution


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
    amount: Optional[float] = None
    qty: Optional[int] = None
    quotation_id: Optional[int] = None


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
    role: str  # sales_rep / sales_manager / finance (admin cannot self-signup)
    seniority: Optional[int] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    seniority: Optional[int] = None
    status: str = "approved"
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


class PortalSignupOut(BaseModel):
    status: str  # "pending" (new/unapproved company) | "approved" (logged in immediately)
    customer_user_id: int
    customer_id: int
    access_token: Optional[str] = None
    token_type: str = "bearer"


class PortalMagicLinkIn(BaseModel):
    email: str


class PortalMagicLinkOut(BaseModel):
    # No email service is wired up — normally this token would be emailed,
    # not returned directly. Returned here so the flow is testable end-to-end.
    magic_link_token: str


class CustomerSignupIn(BaseModel):
    company_name: str
    email: str
    password: str
    # No tier field -- default_tier is never customer-chosen. It starts at
    # "Bronze" and is recalculated automatically from completed order
    # volume (see api.tiering.recalc_customer_tier), so a bigger, more
    # frequent buyer earns a higher tier (and its higher discount ceiling)
    # instead of self-selecting one at signup.


class CustomerIn(BaseModel):
    name: str
    # No tier field -- every customer starts Bronze and earns its way up
    # (see api.tiering), whether created here or via portal self-signup.


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    default_tier: str
    status: str = "approved"
    created_at: datetime


class CustomerApprovalActionIn(BaseModel):
    note: Optional[str] = None


class CustomerUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    email: str
    auth_method: str
    created_at: datetime


class PortalMeOut(BaseModel):
    customer_user: CustomerUserOut
    customer: CustomerOut


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
    replenishment_rules: dict[str, Any] = {}


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
    currency: str = "INR"
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
    amount: Optional[float] = None
    qty: Optional[int] = None


class CreditNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subscription_id: Optional[int] = None
    invoice_id: Optional[int] = None
    amount: float
    reason: Optional[str] = None
    created_at: datetime


class SubscriptionUpdateOut(BaseModel):
    subscription: SubscriptionOut
    # Real mid-cycle proration (PDF B7), computed from amount/qty deltas
    # against days remaining in the current billing cycle. Positive means an
    # additional charge is owed (no invoice auto-generated for it yet -- raise
    # one manually via POST /invoices); negative means a CreditNote was
    # auto-created for the difference.
    proration_amount: Optional[float] = None
    credit_note: Optional[CreditNoteOut] = None


class SubscriptionCancelIn(BaseModel):
    reason: Optional[str] = None
    # Optional override. When omitted and the subscription has amount +
    # next_bill_date set, the refund is computed automatically as
    # amount * (days_remaining_in_cycle / cycle_length_days).
    refund_amount: Optional[float] = None


# ---- Reporting ----

class ReportSummaryOut(BaseModel):
    quotes_created: int
    avg_approval_time_hours: Optional[float] = None
    top_discounted_product: Optional[str] = None
    matching_quotations: list[dict[str, Any]]


# ---- Dashboard (PDF wireframe screen 2) ----

class DashboardSummaryOut(BaseModel):
    pending_approvals: int
    open_quotations: int
    at_risk_deals: int
    recent_activity: list[dict[str, Any]] = []


# ---- Deal health actions (nudge / escalate) ----

class DealHealthActionIn(BaseModel):
    user: Optional[str] = None
    note: Optional[str] = None


class DealHealthActionOut(BaseModel):
    status: str
    action: str
    quotation_id: int


# ---- Admin: user approval ----

class UserApprovalActionIn(BaseModel):
    note: Optional[str] = None


# ---- Razorpay ----

class RazorpayOrderOut(BaseModel):
    order_id: str
    amount: int  # paise
    currency: str = "INR"
    key_id: str
    invoice_id: int


class RazorpayVerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
