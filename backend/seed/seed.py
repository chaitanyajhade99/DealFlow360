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

from api.approvals import decide_approval
from api.quotations import score_and_route
from api.schemas import ApprovalDecisionIn
from seed.bulk_data import RNG, build_companies, build_products, random_email, random_person_name
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

        # Extra Indian-named sales org so quotation volume can be spread
        # across a realistic-sized team, not just 2 reps.
        extra_internal = [
            ("Rohan Mehta", "sales_rep", 2), ("Ananya Kulkarni", "sales_rep", 1),
            ("Vikram Chatterjee", "sales_rep", 0), ("Sneha Malhotra", "sales_rep", 1),
            ("Arjun Naidu", "sales_rep", 2), ("Divya Pillai", "sales_rep", 0),
            ("Karan Deshmukh", "sales_manager", None), ("Priya Banerjee", "sales_manager", None),
            ("Suresh Yadav", "finance", None), ("Meera Joshi", "finance", None),
        ]
        extra_users = []
        for i, (name, role, seniority) in enumerate(extra_internal):
            email = f"{name.lower().replace(' ', '.')}@dealflow360.example"
            extra_users.append(User(name=name, email=email, password_hash=hash_password(SEED_PASSWORD), role=role, seniority=seniority))
        db.add_all(extra_users)

        # A couple of internal sign-ups still awaiting Admin approval -- real
        # data for the User Approvals screen instead of an empty queue.
        db.add_all([
            User(name="Farhan Sheikh", email="farhan.sheikh@dealflow360.example",
                 password_hash=hash_password(SEED_PASSWORD), role="sales_rep", status="pending"),
            User(name="Ritu Chawla", email="ritu.chawla@dealflow360.example",
                 password_hash=hash_password(SEED_PASSWORD), role="finance", status="pending"),
        ])
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
            product_id=products_by_code["LAPTOP-PRO-14"].id, customer_tier="Gold", currency="INR",
            price_rule={"type": "fixed", "price": 1150.00},
        ))
        db.add(UpsellRule(
            source_product_id=products_by_code["LAPTOP-PRO-14"].id,
            suggested_product_id=products_by_code["DOCKING-STATION"].id,
            is_promoted=True, min_margin_pct=12, suggestion_type="cross_sell",
        ))
        db.add(UpsellRule(
            source_product_id=products_by_code["LAPTOP-PRO-14"].id,
            suggested_product_id=products_by_code["EXT-WARRANTY"].id,
            is_promoted=True, min_margin_pct=10, suggestion_type="upsell",
        ))
        db.add(UpsellRule(
            source_product_id=products_by_code["NETWORK-SWITCH-24P"].id,
            suggested_product_id=products_by_code["PREMIUM-SUPPORT"].id,
            is_promoted=True, min_margin_pct=15, suggestion_type="upsell",
        ))

        # --- Bulk Indian-market product catalog (~80 SKUs, PDF A2) ---
        bulk_products = build_products()
        for p in bulk_products:
            product = Product(
                product_code=p["code"], name=p["name"], category=p["category"],
                price=p["price"], unit=p["unit"],
                is_subscription=p.get("is_subscription", False),
                recurring_cycle=p.get("recurring_cycle"),
                quantity_on_hand=p.get("quantity_on_hand"),
                tax_pct=18 if p["category"] != "Services" else 18,  # GST standard rate
                cost=p.get("cost"), is_promoted=p.get("is_promoted", False),
                promo_tag=p.get("promo_tag"),
            )
            db.add(product)
            products_by_code[p["code"]] = product
        db.flush()

        # Pair every promoted Hardware/Subscription product with a plausible
        # accessory or service so GET /quotations/{id}/upsell-suggestions
        # (PDF B5) has real coverage across the catalog, not just 2 SKUs.
        hardware_codes = [c for c, prod in products_by_code.items() if prod.category == "Hardware"]
        service_codes = [c for c, prod in products_by_code.items() if prod.category == "Services"]
        subscription_codes = [c for c, prod in products_by_code.items() if prod.category == "Subscription"]
        accessory_pool = hardware_codes + service_codes + subscription_codes
        promoted_sources = [c for c, prod in products_by_code.items() if prod.is_promoted]
        for source_code in promoted_sources:
            candidates = [c for c in accessory_pool if c != source_code]
            for suggested_code in RNG.sample(candidates, k=min(2, len(candidates))):
                suggested_product = products_by_code[suggested_code]
                # Heuristic for the bulk-generated pairs: a Services/Subscription
                # suggestion attaches a richer plan/tier to the same purchase
                # (upsell); a Hardware suggestion is a separate, complementary
                # item (cross_sell). The 3 hand-authored rules above are typed
                # explicitly rather than by this rule.
                suggestion_type = "upsell" if suggested_product.category in ("Services", "Subscription") else "cross_sell"
                db.add(UpsellRule(
                    source_product_id=products_by_code[source_code].id,
                    suggested_product_id=suggested_product.id,
                    is_promoted=suggested_product.is_promoted,
                    min_margin_pct=RNG.choice([8, 10, 12, 15]),
                    suggestion_type=suggestion_type,
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
        db.add(SubscriptionPlan(
            name="Basic Support Plan", cycle="Monthly",
            proration_rule={"mid_cycle_qty_change": "prorate_remaining_days"},
            cancellation_rule={"refund": "none", "notice_days": 7},
        ))
        db.add(SubscriptionPlan(
            name="SLA Gold Support Plan", cycle="Quarterly",
            proration_rule={"mid_cycle_qty_change": "prorate_remaining_days"},
            cancellation_rule={"refund": "partial", "notice_days": 30},
        ))
        db.add(SubscriptionPlan(
            name="AWS Managed Support", cycle="Monthly",
            proration_rule={"mid_cycle_qty_change": "prorate_remaining_days"},
            cancellation_rule={"refund": "full", "notice_days": 15},
        ))

        # --- Extra Indian-city warehouses (PDF A4) -- Main Warehouse + East
        # Depot above stay as the original 2; add 8 more so fulfillment
        # splits have real multi-warehouse variety. ---
        extra_warehouse_cities = [
            "Mumbai", "Bengaluru", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad", "Jaipur",
        ]
        stockable_codes = [c for c, prod in products_by_code.items() if prod.category != "Services"]
        for city in extra_warehouse_cities:
            stock = [
                {"product_id": code, "qty": RNG.randint(3, 120)}
                for code in RNG.sample(stockable_codes, k=min(18, len(stockable_codes)))
            ]
            db.add(Warehouse(
                name=f"{city} Fulfillment Center",
                stock=stock,
                shipping_cost_per_unit=round(RNG.uniform(3.5, 9.0), 2),
                shipment_fixed_cost=round(RNG.uniform(8.0, 25.0), 2),
                replenishment_rules={"reorder_point": RNG.randint(3, 12), "reorder_qty": RNG.randint(20, 60)},
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

        # =====================================================================
        # Bulk Indian-market dataset: ~78 additional customers and ~90+
        # quotations, run through the REAL scoring/approval/invoicing logic
        # (api.quotations.score_and_route, api.approvals.decide_approval) so
        # every status, risk band, invoice, subscription, and tier reflects
        # genuine business rules instead of hand-picked values.
        # =====================================================================
        existing_names = {"Acme Corp", "Beta Industries", "Delta LLC", "Globex Manufacturing", "Initech Solutions"}
        bulk_companies = build_companies(78, existing_names)
        all_reps = [rep, rep2] + [u for u in extra_users if u.role == "sales_rep"]
        product_codes = list(products_by_code.keys())

        bulk_customers = []
        for i, company in enumerate(bulk_companies):
            is_pending = i < 8  # first 8 stay "pending" -- populates the Customer Approvals queue
            customer = Customer(name=company["name"], default_tier="Bronze", status="pending" if is_pending else "approved")
            db.add(customer)
            bulk_customers.append((customer, company, is_pending))
        db.flush()

        # A portal contact for every pending company (that's what put them in
        # the queue) plus roughly half the approved ones (not every company
        # self-registers a portal user).
        for idx, (customer, company, is_pending) in enumerate(bulk_customers):
            if is_pending or idx % 2 == 0:
                person = random_person_name()
                db.add(CustomerUser(
                    customer_id=customer.id, email=random_email(person, company["name"], idx),
                    password_hash=hash_password(SEED_PASSWORD), auth_method="password",
                ))
        db.flush()

        approved_bulk_customers = [c for c, _company, pending in bulk_customers if not pending]

        for customer in approved_bulk_customers:
            n_quotes = 2 if RNG.random() < 0.2 else 1
            for _ in range(n_quotes):
                sales_rep = RNG.choice(all_reps)
                tier = customer.default_tier  # re-read each loop -- may have risen mid-loop
                tier_limits = tiers_by_name[tier].category_limits
                chosen_codes = RNG.sample(product_codes, k=min(RNG.randint(1, 4), len(product_codes)))
                risk_roll = RNG.random()
                created_days_ago = RNG.randint(0, 45)

                q = Quotation(
                    customer_name=customer.name, customer_tier=tier, status="draft",
                    sales_rep_id=sales_rep.id, created_at=days_ago(created_days_ago),
                    expected_delivery_date=date.today() + timedelta(days=RNG.randint(-5, 30)),
                )
                db.add(q)
                db.flush()

                for code in chosen_codes:
                    product = products_by_code[code]
                    limit = tier_limits.get(product.category, 5)
                    if risk_roll < 0.55:
                        discount = round(RNG.uniform(0, max(limit - 1, 0.5)), 1)  # within limit
                    elif risk_roll < 0.8:
                        discount = round(limit + RNG.uniform(0.5, 3), 1)  # mildly over -> MEDIUM
                    else:
                        discount = round(limit + RNG.uniform(4, 12), 1)  # well over -> HIGH
                    db.add(QuotationLine(
                        quotation_id=q.id, product_id=code, category=product.category,
                        qty=RNG.randint(1, 12), unit_price=float(product.price),
                        discount_pct=discount, category_limit_pct=limit,
                    ))
                db.flush()

                approval = score_and_route(db, q)
                db.flush()

                # Simulate a decision on most non-LOW quotations so the
                # Approvals queue isn't just an unworked backlog -- ~65% get
                # resolved, ~35% stay genuinely pending for the demo.
                if approval.stage in ("sales_manager", "finance") and RNG.random() < 0.65:
                    outcome_roll = RNG.random()
                    if outcome_roll < 0.7:
                        action, note = "approve", "Approved within acceptable commercial terms."
                    elif outcome_roll < 0.87:
                        action, note = "reject", "Discount erodes margin beyond policy floor."
                    else:
                        action, note = "return", "Please revise the discount and resubmit."
                    approval = decide_approval(approval.id, ApprovalDecisionIn(action=action, user="M. Shah", note=note), db)
                    db.flush()
                    # HIGH-risk approvals at sales_manager escalate to finance
                    # -- close ~70% of those too for a real two-step chain.
                    if approval.stage == "finance" and RNG.random() < 0.7:
                        approval = decide_approval(
                            approval.id,
                            ApprovalDecisionIn(action="approve", user="K. Iyer", note="Finance sign-off granted."),
                            db,
                        )
                        db.flush()

                # A slice of newly-confirmed deals get countered by the
                # customer post-confirmation -- gives the portal negotiation
                # flow live data across many accounts, not just one.
                cu = db.query(CustomerUser).filter_by(customer_id=customer.id).first()
                if q.status == "confirmed" and cu and RNG.random() < 0.12:
                    line = db.query(QuotationLine).filter_by(quotation_id=q.id).first()
                    if line:
                        q.status = "negotiation"
                        db.add(NegotiationRequest(
                            quotation_id=q.id, quotation_line_id=line.id, customer_user_id=cu.id,
                            message="Could we get a better rate on this line for a larger repeat order?",
                            counter_discount_pct=round(float(line.discount_pct) + RNG.uniform(2, 6), 1),
                            status="pending", created_at=days_ago(max(created_days_ago - 1, 0)),
                        ))

                # Settle payment on a majority of invoiced deals -- a mix of
                # the real Razorpay path and manual reconciliation, leaving
                # some genuinely outstanding.
                invoice = db.query(Invoice).filter_by(quotation_id=q.id).first()
                if invoice and RNG.random() < 0.55:
                    method = "razorpay" if RNG.random() < 0.6 else "bank_transfer"
                    db.add(Payment(
                        invoice_id=invoice.id, amount=invoice.amount, method=method,
                        paid_at=days_ago(max(created_days_ago - RNG.randint(1, 10), 0)),
                    ))
                    invoice.status = "paid"

                # A Subscription-category line on a confirmed/approved deal
                # becomes a real recurring subscription (PDF A5/B7).
                sub_line = next((l for l in q.lines if l.category == "Subscription"), None)
                if sub_line and q.status in ("confirmed", "approved"):
                    sub_amount = round(float(sub_line.unit_price) * sub_line.qty * (1 - float(sub_line.discount_pct) / 100), 2)
                    is_cancelled = RNG.random() < 0.12
                    sub = Subscription(
                        customer_name=customer.name, plan=products_by_code[sub_line.product_id].name,
                        cycle="Monthly", quotation_id=q.id, amount=sub_amount, qty=sub_line.qty,
                        next_bill_date=None if is_cancelled else date.today() + timedelta(days=RNG.randint(3, 28)),
                        status="cancelled" if is_cancelled else "active",
                    )
                    db.add(sub)
                    db.flush()
                    if is_cancelled:
                        db.add(CreditNote(
                            subscription_id=sub.id, amount=round(sub_amount * RNG.uniform(0.2, 0.6), 2),
                            reason="Prorated refund on early cancellation",
                            created_at=days_ago(max(created_days_ago - 2, 0)),
                        ))

        db.flush()

        total_customers = db.query(Customer).count()
        total_products = db.query(Product).count()
        total_quotations = db.query(Quotation).count()
        total_users = db.query(User).count()
        total_warehouses = db.query(Warehouse).count()

        db.commit()
        print(
            f"Seed complete: {total_users} internal users, {total_warehouses} warehouses, "
            f"3 discount tiers, {total_products} products, 5 subscription plans, "
            f"{total_customers} customers, {total_quotations} quotations spanning every "
            "status and risk band, generated via the real scoring/approval engine.\n"
            f"Test login password for every seeded user: {SEED_PASSWORD}\n"
            "All internal endpoints require Authorization: Bearer <token> from "
            "POST /auth/login; portal endpoints require a token from POST /portal/login."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
