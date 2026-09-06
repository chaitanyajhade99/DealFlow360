"""Regression tests for the 2026-09-06 production-readiness pass (see
API_CONTRACT.md's changelog block of the same name).

These run against the app's REAL configured database (whatever DATABASE_URL
points at when pytest runs), not an isolated in-memory/test DB -- there was
no API-level test harness before this pass, and standing up a fully isolated
Postgres fixture is a bigger undertaking than this pass covers. Each test
creates and cleans up its own rows so it's safe to run repeatedly against a
shared dev/demo database, but it is NOT safe to point at a database anyone
else is actively using at the same time. A follow-up worth doing: a
docker-compose test Postgres + fixture-scoped transactions per test.

Run: cd backend && pytest tests/test_production_readiness.py -v
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from models import (
    Approval, FulfillmentSplit, Invoice, Payment, Quotation, QuotationLine, Subscription, get_db,
)

client = TestClient(app)


@pytest.fixture()
def db():
    # Function-scoped and rolled back on any leftover error state -- a
    # module-scoped session would let one test's failed statement poison
    # every later test's cleanup in the same file (Postgres aborts the
    # whole transaction on the first error until a rollback).
    session = next(get_db())
    yield session
    session.rollback()


def _login(email, password="password123"):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def rep_token():
    return _login("j.rao@dealflow360.example")


@pytest.fixture(scope="module")
def manager_token():
    return _login("m.shah@dealflow360.example")


@pytest.fixture(scope="module")
def finance_token():
    return _login("k.iyer@dealflow360.example")


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@dealflow360.example")


def _cleanup_quotation(db, quotation_id):
    db.query(Subscription).filter(Subscription.quotation_id == quotation_id).delete()
    invoice_ids = [i.id for i in db.query(Invoice.id).filter(Invoice.quotation_id == quotation_id).all()]
    if invoice_ids:
        db.query(Payment).filter(Payment.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
    db.query(Invoice).filter(Invoice.quotation_id == quotation_id).delete()
    db.query(FulfillmentSplit).filter(FulfillmentSplit.quotation_id == quotation_id).delete()
    db.query(Approval).filter(Approval.quotation_id == quotation_id).delete()
    db.query(QuotationLine).filter(QuotationLine.quotation_id == quotation_id).delete()
    db.query(Quotation).filter(Quotation.id == quotation_id).delete()
    db.commit()


# ---------------------------------------------------------------------------
# RBAC: Admin-only backend configuration
# ---------------------------------------------------------------------------

class TestAdminConfigRBAC:
    def test_rep_cannot_write_discount_tier(self, rep_token):
        resp = client.post(
            "/discount-tiers", headers=_auth(rep_token),
            json={"name": "PytestTier", "max_discount_pct": 50, "category_limits": {}},
        )
        assert resp.status_code == 403

    def test_manager_can_write_discount_tier(self, manager_token, db):
        resp = client.post(
            "/discount-tiers", headers=_auth(manager_token),
            json={"name": "PytestTierMgr", "max_discount_pct": 12, "category_limits": {}},
        )
        assert resp.status_code == 200, resp.text
        from models import DiscountTier
        db.query(DiscountTier).filter(DiscountTier.name == "PytestTierMgr").delete()
        db.commit()

    def test_rep_cannot_write_warehouse(self, rep_token):
        resp = client.post(
            "/warehouses", headers=_auth(rep_token),
            json={"name": "Pytest Depot", "stock": [], "shipping_cost_per_unit": 1, "shipment_fixed_cost": 1},
        )
        assert resp.status_code == 403

    def test_admin_can_write_warehouse(self, admin_token, db):
        resp = client.post(
            "/warehouses", headers=_auth(admin_token),
            json={"name": "Pytest Depot Admin", "stock": [], "shipping_cost_per_unit": 1, "shipment_fixed_cost": 1},
        )
        assert resp.status_code == 200, resp.text
        from models import Warehouse
        db.query(Warehouse).filter(Warehouse.name == "Pytest Depot Admin").delete()
        db.commit()

    def test_rep_can_still_read_quote_building_config(self, rep_token):
        # A rep needs to read products/discount tiers to build a quote --
        # these stay open to every internal role.
        for path in ("/products", "/discount-tiers"):
            assert client.get(path, headers=_auth(rep_token)).status_code == 200

    def test_rep_cannot_read_warehouses_or_invoices(self, rep_token):
        # PS section 3: warehouse fulfillment management and billing
        # reconciliation belong to Finance/Operations, not the Sales Rep --
        # gated for reads too, not just writes.
        assert client.get("/warehouses", headers=_auth(rep_token)).status_code == 403
        assert client.get("/invoices", headers=_auth(rep_token)).status_code == 403

    def test_finance_can_read_warehouses_and_invoices(self, finance_token):
        assert client.get("/warehouses", headers=_auth(finance_token)).status_code == 200
        assert client.get("/invoices", headers=_auth(finance_token)).status_code == 200


# ---------------------------------------------------------------------------
# RBAC + state machine: approval decisions
# ---------------------------------------------------------------------------

class TestApprovalRBACAndStateMachine:
    @pytest.fixture()
    def high_risk_approval(self, db, rep_token):
        resp = client.post(
            "/quotations", headers=_auth(rep_token),
            json={
                "customer_name": "Globex Manufacturing", "customer_tier": "Gold",
                "lines": [{"product_id": "ONSITE-SETUP", "category": "Services", "qty": 1, "unit_price": 1, "discount_pct": 18}],
            },
        )
        assert resp.status_code == 200, resp.text
        qid = resp.json()["id"]
        submit = client.post(f"/quotations/{qid}/submit", headers=_auth(rep_token))
        assert submit.status_code == 200, submit.text
        approval = submit.json()
        assert approval["blended_risk"] in ("MEDIUM", "HIGH")
        yield qid, approval["id"]
        _cleanup_quotation(db, qid)

    def test_rep_cannot_decide_own_approval(self, rep_token, high_risk_approval):
        _, approval_id = high_risk_approval
        resp = client.post(
            f"/approvals/{approval_id}/decision", headers=_auth(rep_token),
            json={"action": "approve"},
        )
        assert resp.status_code == 403

    def test_manager_can_decide_sales_manager_stage(self, manager_token, high_risk_approval):
        _, approval_id = high_risk_approval
        resp = client.post(
            f"/approvals/{approval_id}/decision", headers=_auth(manager_token),
            json={"action": "return", "note": "pytest"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["stage"] == "returned"

    def test_cannot_redecide_resolved_approval(self, manager_token, high_risk_approval):
        _, approval_id = high_risk_approval
        first = client.post(
            f"/approvals/{approval_id}/decision", headers=_auth(manager_token),
            json={"action": "reject"},
        )
        assert first.status_code == 200
        second = client.post(
            f"/approvals/{approval_id}/decision", headers=_auth(manager_token),
            json={"action": "approve"},
        )
        assert second.status_code == 400

    def test_cannot_edit_lines_of_confirmed_quotation(self, rep_token, db):
        resp = client.post(
            "/quotations", headers=_auth(rep_token),
            json={
                "customer_name": "Beta Industries", "customer_tier": "Silver",
                "lines": [{"product_id": "LAPTOP-PRO-14", "category": "Hardware", "qty": 1, "unit_price": 1, "discount_pct": 0}],
            },
        )
        qid = resp.json()["id"]
        submit = client.post(f"/quotations/{qid}/submit", headers=_auth(rep_token))
        assert submit.json()["stage"] == "confirmed"

        edit = client.patch(
            f"/quotations/{qid}/lines", headers=_auth(rep_token),
            json={"lines": [{"product_id": "LAPTOP-PRO-14", "category": "Hardware", "qty": 5, "unit_price": 1, "discount_pct": 0}]},
        )
        assert edit.status_code == 400
        _cleanup_quotation(db, qid)


# ---------------------------------------------------------------------------
# Hybrid billing: subscription lines create a real Subscription
# ---------------------------------------------------------------------------

class TestHybridBilling:
    def test_confirm_creates_subscription_and_excludes_it_from_invoice(self, rep_token, db):
        resp = client.post(
            "/quotations", headers=_auth(rep_token),
            json={
                "customer_name": "Delta LLC", "customer_tier": "Bronze",
                "lines": [
                    {"product_id": "LAPTOP-PRO-14", "category": "Hardware", "qty": 1, "unit_price": 1, "discount_pct": 0},
                    {"product_id": "CARE-PLAN-2YR", "category": "Subscription", "qty": 1, "unit_price": 1, "discount_pct": 0},
                ],
            },
        )
        qid = resp.json()["id"]
        submit = client.post(f"/quotations/{qid}/submit", headers=_auth(rep_token))
        assert submit.json()["stage"] == "confirmed"

        invoice = db.query(Invoice).filter(Invoice.quotation_id == qid).first()
        assert invoice is not None
        assert float(invoice.amount) == 1200.0  # laptop only, subscription excluded

        sub = db.query(Subscription).filter(Subscription.quotation_id == qid).first()
        assert sub is not None
        assert sub.plan == "CARE-PLAN-2YR"
        assert float(sub.amount) == 199.0

        # Idempotency: re-running must not duplicate the subscription
        from api.invoices import create_invoice_if_needed
        q = db.get(Quotation, qid)
        create_invoice_if_needed(db, q)
        db.commit()
        count = db.query(Subscription).filter(Subscription.quotation_id == qid).count()
        assert count == 1

        _cleanup_quotation(db, qid)


# ---------------------------------------------------------------------------
# Price lists
# ---------------------------------------------------------------------------

class TestPriceListResolution:
    def test_tier_price_override_applied(self, rep_token, db):
        resp = client.post(
            "/quotations", headers=_auth(rep_token),
            json={
                "customer_name": "Globex Manufacturing", "customer_tier": "Gold",
                "lines": [{"product_id": "LAPTOP-PRO-14", "category": "Hardware", "qty": 1, "unit_price": 1, "discount_pct": 0}],
            },
        )
        qid = resp.json()["id"]
        assert resp.json()["lines"][0]["unit_price"] == 1150.0  # seeded Gold price-list override
        _cleanup_quotation(db, qid)

    def test_base_price_when_no_override(self, rep_token, db):
        resp = client.post(
            "/quotations", headers=_auth(rep_token),
            json={
                "customer_name": "Delta LLC", "customer_tier": "Bronze",
                "lines": [{"product_id": "LAPTOP-PRO-14", "category": "Hardware", "qty": 1, "unit_price": 1, "discount_pct": 0}],
            },
        )
        qid = resp.json()["id"]
        assert resp.json()["lines"][0]["unit_price"] == 1200.0
        _cleanup_quotation(db, qid)


# ---------------------------------------------------------------------------
# Payment integrity
# ---------------------------------------------------------------------------

class TestPaymentIntegrity:
    @pytest.fixture()
    def unpaid_invoice(self, db, rep_token):
        resp = client.post(
            "/quotations", headers=_auth(rep_token),
            json={
                "customer_name": "Beta Industries", "customer_tier": "Silver",
                "lines": [{"product_id": "LAPTOP-PRO-14", "category": "Hardware", "qty": 1, "unit_price": 1, "discount_pct": 0}],
            },
        )
        qid = resp.json()["id"]
        client.post(f"/quotations/{qid}/submit", headers=_auth(rep_token))
        invoice = db.query(Invoice).filter(Invoice.quotation_id == qid).first()
        yield invoice.id, float(invoice.amount)
        _cleanup_quotation(db, qid)

    def test_rep_cannot_record_payment(self, rep_token, unpaid_invoice):
        invoice_id, amount = unpaid_invoice
        resp = client.post(f"/invoices/{invoice_id}/pay", headers=_auth(rep_token), json={"amount": amount, "method": "bank_transfer"})
        assert resp.status_code == 403

    def test_negative_amount_rejected(self, finance_token, unpaid_invoice):
        invoice_id, _ = unpaid_invoice
        resp = client.post(f"/invoices/{invoice_id}/pay", headers=_auth(finance_token), json={"amount": -5, "method": "bank_transfer"})
        assert resp.status_code == 400

    def test_excessive_amount_rejected(self, finance_token, unpaid_invoice):
        invoice_id, amount = unpaid_invoice
        resp = client.post(f"/invoices/{invoice_id}/pay", headers=_auth(finance_token), json={"amount": amount * 10, "method": "bank_transfer"})
        assert resp.status_code == 400

    def test_full_payment_then_duplicate_rejected(self, finance_token, unpaid_invoice):
        invoice_id, amount = unpaid_invoice
        first = client.post(f"/invoices/{invoice_id}/pay", headers=_auth(finance_token), json={"amount": amount, "method": "bank_transfer"})
        assert first.status_code == 200
        second = client.post(f"/invoices/{invoice_id}/pay", headers=_auth(finance_token), json={"amount": amount, "method": "bank_transfer"})
        assert second.status_code == 400


# ---------------------------------------------------------------------------
# Fulfillment manual override
# ---------------------------------------------------------------------------

class TestFulfillmentOverride:
    @pytest.fixture()
    def quotation_with_stock_product(self, db, rep_token):
        resp = client.post(
            "/quotations", headers=_auth(rep_token),
            json={
                "customer_name": "Delta LLC", "customer_tier": "Bronze",
                "lines": [{"product_id": "LAPTOP-PRO-14", "category": "Hardware", "qty": 2, "unit_price": 1, "discount_pct": 0}],
            },
        )
        qid = resp.json()["id"]
        yield qid
        _cleanup_quotation(db, qid)

    def test_rep_cannot_override_fulfillment(self, rep_token, quotation_with_stock_product):
        # PS section 3: this is Finance/Operations' job, not the rep's.
        qid = quotation_with_stock_product
        resp = client.post(
            f"/fulfillment/{qid}/override", headers=_auth(rep_token),
            json=[{"product_id": "LAPTOP-PRO-14", "warehouse_id": 1, "qty": 1}],
        )
        assert resp.status_code == 403

    def test_over_allocation_rejected(self, finance_token, quotation_with_stock_product):
        qid = quotation_with_stock_product
        resp = client.post(
            f"/fulfillment/{qid}/override", headers=_auth(finance_token),
            json=[{"product_id": "LAPTOP-PRO-14", "warehouse_id": 1, "qty": 999}],
        )
        assert resp.status_code == 400
        assert "exceeds" in resp.json()["detail"] or "only has" in resp.json()["detail"]

    def test_unknown_product_rejected(self, finance_token, quotation_with_stock_product):
        qid = quotation_with_stock_product
        resp = client.post(
            f"/fulfillment/{qid}/override", headers=_auth(finance_token),
            json=[{"product_id": "NOT-ON-QUOTE", "warehouse_id": 1, "qty": 1}],
        )
        assert resp.status_code == 400

    def test_valid_override_persists_and_survives_get(self, rep_token, finance_token, quotation_with_stock_product):
        qid = quotation_with_stock_product
        override = client.post(
            f"/fulfillment/{qid}/override", headers=_auth(finance_token),
            json=[{"product_id": "LAPTOP-PRO-14", "warehouse_id": 1, "qty": 1}],
        )
        assert override.status_code == 200, override.text
        body = override.json()
        assert body["is_manual_override"] is True
        assert body["backorders"][0]["qty"] == 1  # 2 required, only 1 allocated

        # GET must NOT clobber the manual override with a fresh auto-suggestion
        # -- read access itself stays open to the rep (tracking progress),
        # only the override/reset mutations are Finance/Admin-only.
        again = client.get(f"/fulfillment/{qid}", headers=_auth(rep_token))
        assert again.status_code == 200
        assert again.json()["is_manual_override"] is True
        assert again.json()["splits"] == body["splits"]

    def test_reset_returns_to_auto_split(self, finance_token, quotation_with_stock_product):
        qid = quotation_with_stock_product
        client.post(
            f"/fulfillment/{qid}/override", headers=_auth(finance_token),
            json=[{"product_id": "LAPTOP-PRO-14", "warehouse_id": 1, "qty": 1}],
        )
        reset = client.post(f"/fulfillment/{qid}/reset", headers=_auth(finance_token))
        assert reset.status_code == 200
        assert reset.json()["is_manual_override"] is False
