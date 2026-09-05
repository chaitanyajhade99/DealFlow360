"""Seed sample data for local development / demo.

Run from the backend/ directory:
    python -m seed.seed

Note: QuotationLine.product_id stays a free-text string (per API_CONTRACT.md,
unchanged to avoid an ALTER on the deployed table) rather than an FK to
Product.id. The Product rows below use the same string as product_code so
both the old string-based lines and the new Product/PriceList/UpsellRule
tables refer to the same catalog consistently.

This seed intentionally covers every quotation status (draft,
pending_approval, negotiation, approved, confirmed, rejected) across five
customers, with a full spread of approvals, invoices, payments, credit
notes, and audit history -- so every screen (dashboard, reports, deal
health, kanban) has real, varied data to render instead of one or two
sparse rows.

Test credentials (all use the same password for convenience):
    Internal:  j.rao@dealflow360.example        / password123  (sales_rep)
               m.shah@dealflow360.example       / password123  (sales_manager)
               k.iyer@dealflow360.example       / password123  (finance)
               admin@dealflow360.example        / password123  (admin)
    Portal:    procurement@acme.example         / password123  (Acme Corp)
               ops@globex.example               / password123  (Globex Manufacturing)
"""
from datetime import date, datetime, timedelta, timezone

from models import (
    Approval,
    AuditLog,
    CreditNote,
    Customer,
    CustomerUser,
    DiscountTier,
    Invoice,
    NegotiationRequest,
    Payment,
    PriceList,
    Product,
    ProductVariant,
    Quotation,
    QuotationLine,
    Subscription,
    SubscriptionPlan,
    UpsellRule,
    User,
    Warehouse,
)
from models.database import Base, SessionLocal, engine
from api.auth_utils import hash_password

SEED_PASSWORD = "password123"

# Bronze up to 5%, Silver up to 10%, Gold up to 15% (per PDF section 10)
DISCOUNT_TIERS = [
    {
        "name": "Bronze",
        "max_discount_pct": 5,
        "category_limits": {"Hardware": 5, "Services": 3, "Subscription": 5},
        "approval_chain": {"LOW": "none", "MEDIUM": "sales_manager", "HIGH": "sales_manager_then_finance"},
    },
    {
        "name": "Silver",
        "max_discount_pct": 10,
        "category_limits": {"Hardware": 10, "Services": 7, "Subscription": 8},
        "approval_chain": {"LOW": "none", "MEDIUM": "sales_manager", "HIGH": "sales_manager_then_finance"},
    },
    {
        "name": "Gold",
        "max_discount_pct": 15,
        "category_limits": {"Hardware": 15, "Services": 10, "Subscription": 10},
        "approval_chain": {"LOW": "none", "MEDIUM": "sales_manager", "HIGH": "sales_manager_then_finance"},
    },
]

PRODUCTS = [
    {"code": "LAPTOP-PRO-14", "name": "Laptop Pro 14", "category": "Hardware", "price": 1200.00, "unit": "each",
     "cost": 850.00, "is_promoted": False, "promo_tag": None},
    {"code": "DOCKING-STATION", "name": "Docking Station", "category": "Hardware", "price": 150.00, "unit": "each",
     "cost": 95.00, "is_promoted": True, "promo_tag": "Bundle Deal"},
    {"code": "NETWORK-SWITCH-24P", "name": "24-Port Network Switch", "category": "Hardware", "price": 620.00, "unit": "each",
     "cost": 410.00, "is_promoted": False, "promo_tag": None},
    {"code": "ONSITE-SETUP", "name": "Onsite Setup Service", "category": "Services", "price": 450.00, "unit": "engagement",
     "cost": 300.00, "is_promoted": False, "promo_tag": None},
    {"code": "EXT-WARRANTY", "name": "Extended Warranty", "category": "Services", "price": 180.00, "unit": "each",
     "cost": 60.00, "is_promoted": True, "promo_tag": "High Margin"},
    {"code": "CARE-PLAN-2YR", "name": "Care Plan 2yr", "category": "Subscription", "price": 199.00, "unit": "license",
     "is_subscription": True, "recurring_cycle": "Monthly",
     "cost": 40.00, "is_promoted": True, "promo_tag": "Recurring Revenue"},
    {"code": "PREMIUM-SUPPORT", "name": "Premium Support Plan", "category": "Subscription", "price": 349.00, "unit": "license",
     "is_subscription": True, "recurring_cycle": "Monthly",
     "cost": 90.00, "is_promoted": True, "promo_tag": "SLA Upgrade"},
]

WAREHOUSE_SHIPPING = {
    "Main Warehouse": {"shipping_cost_per_unit": 4.50, "shipment_fixed_cost": 12.00},
    "East Depot": {"shipping_cost_per_unit": 6.75, "shipment_fixed_cost": 18.00},
}

# PDF A4: "configure ... replenishment rules per warehouse".
WAREHOUSE_REPLENISHMENT = {
    "Main Warehouse": {"reorder_point": 10, "reorder_qty": 40},
    "East Depot": {"reorder_point": 5, "reorder_qty": 25},
}


def days_ago(n):
    return datetime.now(timezone.utc) - timedelta(days=n)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # --- Internal users (PDF section 3 / A1) ---
        rep = User(name="J. Rao", email="j.rao@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="sales_rep", seniority=1)
        rep2 = User(name="P. Nair", email="p.nair@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="sales_rep", seniority=0)
        manager = User(name="M. Shah", email="m.shah@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="sales_manager")
        finance = User(name="K. Iyer", email="k.iyer@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="finance")
        admin = User(name="Admin", email="admin@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="admin")
        db.add_all([rep, rep2, manager, finance, admin])
        db.flush()

        # --- Warehouses ---
        main_wh = Warehouse(
            name="Main Warehouse",
            stock=[
                {"product_id": "LAPTOP-PRO-14", "qty": 22},
                {"product_id": "DOCKING-STATION", "qty": 12},
                {"product_id": "NETWORK-SWITCH-24P", "qty": 15},
                {"product_id": "ONSITE-SETUP", "qty": 999},
                {"product_id": "EXT-WARRANTY", "qty": 999},
                {"product_id": "CARE-PLAN-2YR", "qty": 999},
                {"product_id": "PREMIUM-SUPPORT", "qty": 999},
            ],
            **WAREHOUSE_SHIPPING["Main Warehouse"],
            replenishment_rules=WAREHOUSE_REPLENISHMENT["Main Warehouse"],
        )
        east_depot = Warehouse(
            name="East Depot",
            stock=[
                {"product_id": "LAPTOP-PRO-14", "qty": 8},
                {"product_id": "DOCKING-STATION", "qty": 65},
                {"product_id": "NETWORK-SWITCH-24P", "qty": 4},
                {"product_id": "ONSITE-SETUP", "qty": 999},
                {"product_id": "EXT-WARRANTY", "qty": 999},
                {"product_id": "CARE-PLAN-2YR", "qty": 999},
                {"product_id": "PREMIUM-SUPPORT", "qty": 999},
            ],
            **WAREHOUSE_SHIPPING["East Depot"],
            replenishment_rules=WAREHOUSE_REPLENISHMENT["East Depot"],
        )
        db.add_all([main_wh, east_depot])

        # --- Discount tiers ---
        tiers_by_name = {}
        for tier_data in DISCOUNT_TIERS:
            tier = DiscountTier(**tier_data)
            db.add(tier)
            tiers_by_name[tier_data["name"]] = tier
        db.flush()

        # --- Products, variants, price lists ---
        products_by_code = {}
        for p in PRODUCTS:
            product = Product(
                product_code=p["code"], name=p["name"], category=p["category"],
                price=p["price"], unit=p["unit"],
                is_subscription=p.get("is_subscription", False),
                recurring_cycle=p.get("recurring_cycle"),
                quantity_on_hand=p.get("quantity_on_hand"),
                tax_pct=p.get("tax_pct", 8),
                cost=p.get("cost"), is_promoted=p.get("is_promoted", False),
                promo_tag=p.get("promo_tag"),
            )
            db.add(product)
            products_by_code[p["code"]] = product
        db.flush()

        db.add(ProductVariant(
            product_id=products_by_code["LAPTOP-PRO-14"].id, attribute="RAM", value="16GB", extra_price=80.00,
        ))
        db.add(ProductVariant(
            product_id=products_by_code["LAPTOP-PRO-14"].id, attribute="RAM", value="32GB", extra_price=180.00,
        ))
        db.add(PriceList(
            product_id=products_by_code["LAPTOP-PRO-14"].id, customer_tier="Gold", currency="USD",
            price_rule={"type": "fixed", "price": 1150.00},
        ))
        db.add(UpsellRule(
            source_product_id=products_by_code["LAPTOP-PRO-14"].id,
            suggested_product_id=products_by_code["DOCKING-STATION"].id,
            is_promoted=True, min_margin_pct=12,
        ))
        db.add(UpsellRule(
            source_product_id=products_by_code["LAPTOP-PRO-14"].id,
            suggested_product_id=products_by_code["EXT-WARRANTY"].id,
            is_promoted=True, min_margin_pct=10,
        ))
        db.add(UpsellRule(
            source_product_id=products_by_code["NETWORK-SWITCH-24P"].id,
            suggested_product_id=products_by_code["PREMIUM-SUPPORT"].id,
            is_promoted=True, min_margin_pct=15,
        ))

        # --- Subscription plan definitions (PDF A5) ---
        db.add(SubscriptionPlan(
            name="Care Plan 2yr", cycle="Monthly",
            proration_rule={"mid_cycle_qty_change": "prorate_remaining_days"},
            cancellation_rule={"refund": "partial", "notice_days": 30},
        ))
        db.add(SubscriptionPlan(
            name="Premium Support Plan", cycle="Monthly",
            proration_rule={"mid_cycle_qty_change": "prorate_remaining_days"},
            cancellation_rule={"refund": "partial", "notice_days": 15},
        ))

        # --- Customers + portal users (PDF A1 / section 3) ---
        acme_customer = Customer(name="Acme Corp", default_tier="Gold")
        beta_customer = Customer(name="Beta Industries", default_tier="Silver")
        delta_customer = Customer(name="Delta LLC", default_tier="Bronze")
        globex_customer = Customer(name="Globex Manufacturing", default_tier="Gold")
        initech_customer = Customer(name="Initech Solutions", default_tier="Silver")
        db.add_all([acme_customer, beta_customer, delta_customer, globex_customer, initech_customer])
        db.flush()

        db.add(CustomerUser(
            customer_id=acme_customer.id, email="procurement@acme.example",
            password_hash=hash_password(SEED_PASSWORD), auth_method="password",
        ))
        db.add(CustomerUser(
            customer_id=globex_customer.id, email="ops@globex.example",
            password_hash=hash_password(SEED_PASSWORD), auth_method="password",
        ))
        db.flush()

        # =====================================================================
        # Quotation 1: Acme Corp (Gold) -- pending_approval, HIGH risk
        # matches wireframe screen 4 (Q-1042)
        # =====================================================================
        acme = Quotation(
            customer_name="Acme Corp", customer_tier="Gold", status="pending_approval",
            sales_rep_id=rep.id, created_at=days_ago(6),
            expected_delivery_date=date.today() + timedelta(days=10),
        )
        db.add(acme)
        db.flush()
        db.add_all([
            QuotationLine(
                quotation_id=acme.id, product_id="LAPTOP-PRO-14", category="Hardware",
                qty=2, unit_price=1200.00, discount_pct=12,
                category_limit_pct=tiers_by_name["Gold"].category_limits["Hardware"],
            ),
            QuotationLine(
                quotation_id=acme.id, product_id="ONSITE-SETUP", category="Services",
                qty=1, unit_price=450.00, discount_pct=18,
                category_limit_pct=tiers_by_name["Gold"].category_limits["Services"],
            ),
            QuotationLine(
                quotation_id=acme.id, product_id="EXT-WARRANTY", category="Services",
                qty=1, unit_price=180.00, discount_pct=10,
                category_limit_pct=tiers_by_name["Gold"].category_limits["Services"],
            ),
        ])
        db.add(Approval(
            quotation_id=acme.id, blended_risk="HIGH", stage="sales_manager", assigned_to="M. Shah",
            history=[{"user": "system", "action": "flagged", "reason": "Policy rules: ONSITE-SETUP discounted 18.0% against a 10.0% ceiling (8.0 pts over).", "at": days_ago(6).isoformat()}],
            flagged_lines=[{"line": "ONSITE-SETUP", "discount_given_pct": 18.0, "limit_allowed_pct": 10.0, "over_by_pct": 8.0, "line_id": None, "product_id": "ONSITE-SETUP", "category": "Services", "line_value": 450.0}],
        ))
        db.add(AuditLog(
            entity_type="quotation", entity_id=acme.id, user_id=rep.id, action="create",
            reason="Initial quotation build", after={"status": "pending_approval"},
            created_at=days_ago(6),
        ))
        acme_cu = db.query(CustomerUser).filter_by(customer_id=acme_customer.id).first()
        db.add(NegotiationRequest(
            quotation_id=acme.id, customer_user_id=acme_cu.id,
            message="Can the setup fee be 10% off instead of 18%?",
            counter_discount_pct=10, status="pending", created_at=days_ago(2),
        ))

        # =====================================================================
        # Quotation 2: Beta Industries (Silver) -- confirmed, within limits
        # =====================================================================
        beta = Quotation(
            customer_name="Beta Industries", customer_tier="Silver", status="confirmed",
            sales_rep_id=rep.id, created_at=days_ago(20),
            expected_delivery_date=date.today() + timedelta(days=5),
        )
        db.add(beta)
        db.flush()
        db.add(QuotationLine(
            quotation_id=beta.id, product_id="CARE-PLAN-2YR", category="Subscription",
            qty=5, unit_price=199.00, discount_pct=8,
            category_limit_pct=tiers_by_name["Silver"].category_limits["Subscription"],
        ))
        db.add(Approval(
            quotation_id=beta.id, blended_risk="LOW", stage="confirmed",
            history=[{"user": "system", "action": "flagged", "reason": "All lines within their category limits.", "at": days_ago(20).isoformat()}],
            flagged_lines=[],
        ))
        db.add(Subscription(
            customer_name="Beta Industries", plan="Care Plan 2yr", cycle="Monthly",
            next_bill_date=date.today() + timedelta(days=18), status="active",
            amount=round(5 * 199.00 * (1 - 8 / 100), 2), qty=5, quotation_id=beta.id,
        ))
        db.add(Invoice(quotation_id=beta.id, amount=round(5 * 199.00 * (1 - 8 / 100), 2), status="unpaid", due_date=date.today() + timedelta(days=30)))

        # =====================================================================
        # Quotation 3: Delta LLC (Bronze) -- draft, overdue delivery (slippage demo)
        # =====================================================================
        delta = Quotation(
            customer_name="Delta LLC", customer_tier="Bronze", status="draft",
            sales_rep_id=rep2.id, created_at=days_ago(9),
            expected_delivery_date=date.today() - timedelta(days=3),
        )
        db.add(delta)
        db.flush()
        db.add(QuotationLine(
            quotation_id=delta.id, product_id="DOCKING-STATION", category="Hardware",
            qty=10, unit_price=150.00, discount_pct=5,
            category_limit_pct=tiers_by_name["Bronze"].category_limits["Hardware"],
        ))

        # =====================================================================
        # Quotation 4: Globex Manufacturing (Gold) -- approved, paid in full
        # =====================================================================
        globex = Quotation(
            customer_name="Globex Manufacturing", customer_tier="Gold", status="approved",
            sales_rep_id=rep.id, created_at=days_ago(15),
            expected_delivery_date=date.today() - timedelta(days=1), actual_delivery_date=date.today() - timedelta(days=1),
        )
        db.add(globex)
        db.flush()
        db.add_all([
            QuotationLine(
                quotation_id=globex.id, product_id="NETWORK-SWITCH-24P", category="Hardware",
                qty=4, unit_price=620.00, discount_pct=10,
                category_limit_pct=tiers_by_name["Gold"].category_limits["Hardware"],
            ),
            QuotationLine(
                quotation_id=globex.id, product_id="PREMIUM-SUPPORT", category="Subscription",
                qty=8, unit_price=349.00, discount_pct=9,
                category_limit_pct=tiers_by_name["Gold"].category_limits["Subscription"],
            ),
        ])
        globex_approval = Approval(
            quotation_id=globex.id, blended_risk="MEDIUM", stage="confirmed", assigned_to="M. Shah",
            history=[
                {"user": "system", "action": "flagged", "reason": "Blended overage 1.8 pts across 2 lines.", "at": days_ago(15).isoformat()},
                {"user": "M. Shah", "action": "approve", "note": "Within acceptable range for a Gold strategic account.", "at": days_ago(14).isoformat()},
            ],
            flagged_lines=[{"line": "NETWORK-SWITCH-24P", "discount_given_pct": 10.0, "limit_allowed_pct": 15.0, "over_by_pct": 0.0, "line_id": None, "product_id": "NETWORK-SWITCH-24P", "category": "Hardware", "line_value": 2480.0}],
        )
        db.add(globex_approval)
        db.flush()
        db.add(AuditLog(
            entity_type="approval", entity_id=globex_approval.id, action="approve", user_id=manager.id,
            reason="Within acceptable range for a Gold strategic account.",
            before={"stage": "sales_manager"}, after={"stage": "confirmed", "actor": "M. Shah"},
            created_at=days_ago(14),
        ))
        globex_amount = round(4 * 620.00 * (1 - 10 / 100) + 8 * 349.00 * (1 - 9 / 100), 2)
        globex_invoice = Invoice(quotation_id=globex.id, amount=globex_amount, status="paid", due_date=days_ago(-16).date())
        db.add(globex_invoice)
        db.flush()
        db.add(Payment(invoice_id=globex_invoice.id, amount=globex_amount, method="bank_transfer", paid_at=days_ago(10)))
        db.add(Subscription(
            customer_name="Globex Manufacturing", plan="Premium Support Plan", cycle="Monthly",
            next_bill_date=date.today() + timedelta(days=25), status="active",
            amount=round(8 * 349.00 * (1 - 9 / 100), 2), qty=8, quotation_id=globex.id,
        ))

        # =====================================================================
        # Quotation 5: Initech Solutions (Silver) -- rejected by finance
        # =====================================================================
        initech = Quotation(
            customer_name="Initech Solutions", customer_tier="Silver", status="rejected",
            sales_rep_id=rep2.id, created_at=days_ago(11),
        )
        db.add(initech)
        db.flush()
        db.add(QuotationLine(
            quotation_id=initech.id, product_id="LAPTOP-PRO-14", category="Hardware",
            qty=6, unit_price=1200.00, discount_pct=22,
            category_limit_pct=tiers_by_name["Silver"].category_limits["Hardware"],
        ))
        initech_approval = Approval(
            quotation_id=initech.id, blended_risk="HIGH", stage="rejected", assigned_to="K. Iyer",
            history=[
                {"user": "system", "action": "flagged", "reason": "LAPTOP-PRO-14 discounted 22.0% against a 10.0% ceiling (12.0 pts over).", "at": days_ago(11).isoformat()},
                {"user": "M. Shah", "action": "approve", "note": "Escalating -- outside my authority.", "at": days_ago(10).isoformat()},
                {"user": "K. Iyer", "action": "reject", "note": "Discount erodes margin below finance floor for this SKU.", "at": days_ago(9).isoformat()},
            ],
            flagged_lines=[{"line": "LAPTOP-PRO-14", "discount_given_pct": 22.0, "limit_allowed_pct": 10.0, "over_by_pct": 12.0, "line_id": None, "product_id": "LAPTOP-PRO-14", "category": "Hardware", "line_value": 7200.0}],
        )
        db.add(initech_approval)
        db.flush()
        db.add(AuditLog(
            entity_type="approval", entity_id=initech_approval.id, action="reject", user_id=finance.id,
            reason="Discount erodes margin below finance floor for this SKU.",
            before={"stage": "finance"}, after={"stage": "rejected", "actor": "K. Iyer"},
            created_at=days_ago(9),
        ))
        # A subscription that was cancelled with a prorated credit note -- gives
        # credit_notes and billing-history screens real data too.
        cancelled_sub = Subscription(
            customer_name="Initech Solutions", plan="Care Plan 2yr", cycle="Monthly",
            next_bill_date=None, status="cancelled", amount=597.00, qty=3, quotation_id=None,
        )
        db.add(cancelled_sub)
        db.flush()
        db.add(CreditNote(subscription_id=cancelled_sub.id, amount=214.80, reason="Prorated refund on early cancellation", created_at=days_ago(4)))

        # =====================================================================
        # Quotation 6: Acme Corp (Gold) -- second deal, actively under
        # negotiation right now (PDF B8 demo target)
        # =====================================================================
        acme2 = Quotation(
            customer_name="Acme Corp", customer_tier="Gold", status="negotiation",
            sales_rep_id=rep.id, created_at=days_ago(1),
            expected_delivery_date=date.today() + timedelta(days=14),
        )
        db.add(acme2)
        db.flush()
        db.add(QuotationLine(
            quotation_id=acme2.id, product_id="LAPTOP-PRO-14", category="Hardware",
            qty=3, unit_price=1200.00, discount_pct=9,
            category_limit_pct=tiers_by_name["Gold"].category_limits["Hardware"],
        ))
        db.add(Approval(
            quotation_id=acme2.id, blended_risk="LOW", stage="confirmed",
            history=[{"user": "system", "action": "flagged", "reason": "All lines within their category limits.", "at": days_ago(1).isoformat()}],
            flagged_lines=[],
        ))
        db.flush()
        acme2_line = db.query(QuotationLine).filter_by(quotation_id=acme2.id).first()
        db.add(NegotiationRequest(
            quotation_id=acme2.id, quotation_line_id=acme2_line.id, customer_user_id=acme_cu.id,
            message="Would you match 14% off if we commit to 2 more units next quarter?",
            counter_discount_pct=14, status="pending", created_at=days_ago(1),
        ))

        db.commit()
        print(
            "Seed complete: 5 users, 2 warehouses, 3 discount tiers, 7 products "
            "(+2 variants, 1 price list entry, 3 upsell rules), 2 subscription plans, "
            "3 subscriptions (+1 cancelled w/ credit note), 5 customers (+2 portal users), "
            "6 quotations across every status, 2 invoices (1 paid), 1 payment, "
            "3 audit logs, 3 negotiation requests.\n"
            f"Test login password for every seeded user: {SEED_PASSWORD}\n"
            "All internal endpoints require Authorization: Bearer <token> from "
            "POST /auth/login; portal endpoints require a token from POST /portal/login."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
