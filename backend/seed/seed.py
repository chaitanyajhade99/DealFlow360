"""Seed sample data for local development / demo.

Run from the backend/ directory:
    python -m seed.seed

Note: QuotationLine.product_id stays a free-text string (per API_CONTRACT.md,
unchanged to avoid an ALTER on the deployed table) rather than an FK to
Product.id. The Product rows below use the same string as product_code so
both the old string-based lines and the new Product/PriceList/UpsellRule
tables refer to the same catalog consistently.

Auth is implemented now (POST /auth/login, POST /portal/login) — every
seeded user below gets a real bcrypt hash via api.auth_utils.hash_password.
Test credentials (all use the same password for convenience):
    Internal:  j.rao@dealflow360.example        / password123  (sales_rep)
               m.shah@dealflow360.example       / password123  (sales_manager)
               k.iyer@dealflow360.example       / password123  (finance)
               admin@dealflow360.example        / password123  (admin)
    Portal:    procurement@acme.example         / password123
"""
from datetime import date, timedelta

from models import (
    Approval,
    AuditLog,
    Customer,
    CustomerUser,
    DiscountTier,
    NegotiationRequest,
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
    {"code": "ONSITE-SETUP", "name": "Onsite Setup Service", "category": "Services", "price": 450.00, "unit": "engagement",
     "cost": 300.00, "is_promoted": False, "promo_tag": None},
    {"code": "EXT-WARRANTY", "name": "Extended Warranty", "category": "Services", "price": 180.00, "unit": "each",
     "cost": 60.00, "is_promoted": True, "promo_tag": "High Margin"},
    {"code": "CARE-PLAN-2YR", "name": "Care Plan 2yr", "category": "Subscription", "price": 199.00, "unit": "license",
     "is_subscription": True, "recurring_cycle": "Monthly",
     "cost": 40.00, "is_promoted": True, "promo_tag": "Recurring Revenue"},
]

# Main Warehouse is closer/cheaper to ship from than East Depot — matches the
# wireframe treating East Depot as the secondary/split source.
WAREHOUSE_SHIPPING = {
    "Main Warehouse": {"shipping_cost_per_unit": 4.50, "shipment_fixed_cost": 12.00},
    "East Depot": {"shipping_cost_per_unit": 6.75, "shipment_fixed_cost": 18.00},
}

# PDF A4: "configure ... replenishment rules per warehouse".
WAREHOUSE_REPLENISHMENT = {
    "Main Warehouse": {"reorder_point": 10, "reorder_qty": 40},
    "East Depot": {"reorder_point": 5, "reorder_qty": 25},
}


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # --- Internal users (PDF section 3 / A1) ---
        rep = User(name="J. Rao", email="j.rao@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="sales_rep", seniority=1)
        manager = User(name="M. Shah", email="m.shah@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="sales_manager")
        finance = User(name="K. Iyer", email="k.iyer@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="finance")
        admin = User(name="Admin", email="admin@dealflow360.example", password_hash=hash_password(SEED_PASSWORD), role="admin")
        db.add_all([rep, manager, finance, admin])

        # --- Warehouses ---
        main_wh = Warehouse(
            name="Main Warehouse",
            stock=[
                {"product_id": "LAPTOP-PRO-14", "qty": 22},
                {"product_id": "DOCKING-STATION", "qty": 12},
                {"product_id": "ONSITE-SETUP", "qty": 999},
                {"product_id": "EXT-WARRANTY", "qty": 999},
                {"product_id": "CARE-PLAN-2YR", "qty": 999},
            ],
            **WAREHOUSE_SHIPPING["Main Warehouse"],
            replenishment_rules=WAREHOUSE_REPLENISHMENT["Main Warehouse"],
        )
        east_depot = Warehouse(
            name="East Depot",
            stock=[
                {"product_id": "LAPTOP-PRO-14", "qty": 8},
                {"product_id": "DOCKING-STATION", "qty": 65},
                {"product_id": "ONSITE-SETUP", "qty": 999},
                {"product_id": "EXT-WARRANTY", "qty": 999},
                {"product_id": "CARE-PLAN-2YR", "qty": 999},
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
                cost=p.get("cost"), is_promoted=p.get("is_promoted", False),
                promo_tag=p.get("promo_tag"),
            )
            db.add(product)
            products_by_code[p["code"]] = product
        db.flush()

        db.add(ProductVariant(
            product_id=products_by_code["LAPTOP-PRO-14"].id, attribute="RAM", value="16GB", extra_price=80.00,
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

        # --- Subscription plan definitions (PDF A5) ---
        db.add(SubscriptionPlan(
            name="Care Plan 2yr", cycle="Monthly",
            proration_rule={"mid_cycle_qty_change": "prorate_remaining_days"},
            cancellation_rule={"refund": "partial", "notice_days": 30},
        ))

        # --- Customers + portal users (PDF A1 / section 3) ---
        acme_customer = Customer(name="Acme Corp", default_tier="Gold")
        beta_customer = Customer(name="Beta Industries", default_tier="Silver")
        delta_customer = Customer(name="Delta LLC", default_tier="Bronze")
        db.add_all([acme_customer, beta_customer, delta_customer])
        db.flush()

        db.add(CustomerUser(
            customer_id=acme_customer.id, email="procurement@acme.example",
            password_hash=hash_password(SEED_PASSWORD), auth_method="password",
        ))

        # --- Quotation 1: Acme Corp (Gold) — matches wireframe screen 4 (Q-1042) ---
        acme = Quotation(customer_name="Acme Corp", customer_tier="Gold", status="pending_approval", sales_rep_id=rep.id)
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
            quotation_id=acme.id, blended_risk="HIGH", stage="sales_manager",
            assigned_to="M. Shah",
            history=[{"user": "J. Rao", "action": "submitted", "note": None, "at": "2026-08-28T00:00:00Z"}],
        ))
        db.add(AuditLog(
            entity_type="quotation", entity_id=acme.id, user_id=rep.id, action="create",
            reason="Initial quotation build", after={"status": "pending_approval"},
        ))
        db.flush()
        db.add(NegotiationRequest(
            quotation_id=acme.id,
            customer_user_id=db.query(CustomerUser).filter_by(customer_id=acme_customer.id).first().id,
            message="Can the fee be 10% off instead of 18%?",
            counter_discount_pct=10, status="pending",
        ))

        # --- Quotation 2: Beta Industries (Silver) — within limits, no approval needed ---
        beta = Quotation(customer_name="Beta Industries", customer_tier="Silver", status="confirmed", sales_rep_id=rep.id)
        db.add(beta)
        db.flush()
        db.add(QuotationLine(
            quotation_id=beta.id, product_id="CARE-PLAN-2YR", category="Subscription",
            qty=5, unit_price=199.00, discount_pct=8,
            category_limit_pct=tiers_by_name["Silver"].category_limits["Subscription"],
        ))
        db.add(Subscription(
            customer_name="Beta Industries", plan="Care Plan 2yr", cycle="Monthly",
            next_bill_date=date.today() + timedelta(days=18), status="active",
            amount=5 * 199.00 * (1 - 8 / 100), qty=5, quotation_id=beta.id,
        ))

        # --- Quotation 3: Delta LLC (Bronze) — within limits, draft, and overdue
        # on delivery to demo the deal-health delivery-slippage indicator ---
        delta = Quotation(
            customer_name="Delta LLC", customer_tier="Bronze", status="draft", sales_rep_id=rep.id,
            expected_delivery_date=date.today() - timedelta(days=3),
        )
        db.add(delta)
        db.flush()
        db.add(QuotationLine(
            quotation_id=delta.id, product_id="DOCKING-STATION", category="Hardware",
            qty=10, unit_price=150.00, discount_pct=5,
            category_limit_pct=tiers_by_name["Bronze"].category_limits["Hardware"],
        ))

        db.commit()
        print(
            "Seed complete: 4 users, 2 warehouses, 3 discount tiers, 5 products "
            "(+1 variant, 1 price list entry, 1 upsell rule), 1 subscription plan, "
            "1 subscription, 3 customers (+1 portal user), 3 quotations, 1 audit log, "
            "1 negotiation request.\n"
            f"Test login password for every seeded user: {SEED_PASSWORD}\n"
            "All /quotations, /approvals, /warehouses, /products, /subscriptions, "
            "/invoices, /deal-health, /discount-tiers, /reports, /dashboard, "
            "/quotations/*/upsell-suggestions and /fulfillment/* endpoints now "
            "require Authorization: Bearer <token> from POST /auth/login."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
