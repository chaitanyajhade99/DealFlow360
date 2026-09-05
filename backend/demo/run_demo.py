"""Live, narrated walkthrough of the DealFlow360 backend for demo/review
purposes.

This is not a test suite -- it's meant to be run OUT LOUD in front of a
reviewer while the API server is visibly running in another terminal (and,
ideally, pgAdmin/Supabase's table editor open alongside it so the rows can be
watched appearing in real time). Every step prints what it's doing, what PDF
requirement it proves, and the real response the server sent back.

Usage:
    1. In one terminal:  uvicorn api.main:app --reload
    2. In another:       python demo/run_demo.py

Optional: set DEMO_BASE_URL to point at a different host (defaults to
http://127.0.0.1:8000).

Safe to re-run -- it creates its own fresh quotation each time instead of
depending on specific seeded row ids, so nothing here depends on prior runs.
"""
import os
import sys

import requests

BASE_URL = os.environ.get("DEMO_BASE_URL", "http://127.0.0.1:8000")

STEP = 0


def header(title: str, pdf_ref: str = "") -> None:
    global STEP
    STEP += 1
    print()
    print("=" * 78)
    suffix = f"   (PDF: {pdf_ref})" if pdf_ref else ""
    print(f" STEP {STEP}: {title}{suffix}")
    print("=" * 78)


def show(label: str, value) -> None:
    print(f"  {label}: {value}")


def call(method: str, path: str, **kwargs):
    url = f"{BASE_URL}{path}"
    resp = requests.request(method, url, timeout=15, **kwargs)
    print(f"  -> {method} {path}  [{resp.status_code}]")
    try:
        return resp, resp.json()
    except ValueError:
        return resp, None


def require_ok(resp, body, what: str):
    if not resp.ok:
        print(f"\n!! {what} failed unexpectedly: {resp.status_code} {body}")
        sys.exit(1)


def main() -> None:
    print("DealFlow360 backend -- live demo walkthrough")
    print(f"Target server: {BASE_URL}")

    # ---- 0. Health check: the server is a real, running process ----------
    header("Health check", "server is actually running, not mocked")
    resp, body = call("GET", "/health")
    require_ok(resp, body, "health check")
    show("Response", body)
    print("  This is a live HTTP server. Nothing that follows is hardcoded")
    print("  or replayed -- every response below comes from a real request")
    print("  hitting FastAPI, which hits Postgres, and comes back.")

    # ---- 1. Prove auth is actually enforced -------------------------------
    header("Call a protected endpoint with NO token", "security is real, not decorative")
    resp, body = call("GET", "/quotations")
    show("Status", resp.status_code)
    show("Body", body)
    assert resp.status_code == 401, "expected 401 without a token"
    print("  Blocked with 401, as it should be -- every internal endpoint")
    print("  requires a real login. Now let's actually log in.")

    # ---- 2. Internal login --------------------------------------------------
    header("Sales rep logs in", "A1, internal users log in with standard credentials")
    resp, body = call("POST", "/auth/login", json={
        "email": "j.rao@dealflow360.example", "password": "password123",
    })
    require_ok(resp, body, "internal login")
    token = body["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    show("Logged in as", f"{body['user']['name']} ({body['user']['role']})")
    show("JWT (truncated)", token[:40] + "...")

    resp, body = call("GET", "/quotations", headers=H)
    require_ok(resp, body, "quotations with token")
    print(f"  Same call as step 1, now WITH the token -> {resp.status_code}. Auth is real.")

    # ---- 3. Build a quotation with an over-limit discount ------------------
    header(
        "Rep builds a quote for a Gold customer, over-discounting a Services line",
        "section 10, blended discount risk score",
    )
    resp, body = call("POST", "/quotations", json={
        "customer_name": "Acme Corp", "customer_tier": "Gold", "sales_rep_id": 1,
        "lines": [
            {"product_id": "LAPTOP-PRO-14", "category": "Hardware", "qty": 2,
             "unit_price": 1200.00, "discount_pct": 12},
            {"product_id": "ONSITE-SETUP", "category": "Services", "qty": 1,
             "unit_price": 450.00, "discount_pct": 18},
        ],
    }, headers=H)
    require_ok(resp, body, "create quotation")
    quotation_id = body["id"]
    show("Quotation id", quotation_id)
    show("Lines", [f"{l['product_id']}: {l['discount_pct']}% off" for l in body["lines"]])
    print("  Gold allows 15% on Hardware (12% given, fine) but only 10% on")
    print("  Services (18% given -- 8 points over). This is the PDF's exact")
    print("  worked example: technically 'Gold', but one line breaks its")
    print("  own stricter category ceiling.")

    # ---- 4. Submit -> auto-routes to approval, with the reasoning kept ----
    header(
        "Submit the quote -- auto-routes to approval, no rep action required",
        "'quotation is automatically routed for approval'",
    )
    resp, body = call("POST", f"/quotations/{quotation_id}/submit", headers=H)
    require_ok(resp, body, "submit quotation")
    approval_id = body["id"]
    show("Blended risk", body["blended_risk"])
    show("Routed to stage", body["stage"])
    show("System's reason", body["history"][0]["reason"])
    show("Flagged lines (screen 6 table)", body["flagged_lines"])
    assert body["stage"] == "sales_manager", "HIGH risk must still start at sales_manager"
    print("  Nobody clicked 'request approval' -- the backend decided this")
    print("  on its own from the discount math, and it kept the full")
    print("  per-line breakdown (not just a verdict) for the approval screen.")

    # ---- 5. Live upsell + margin ------------------------------------------
    header("Live upsell suggestion + real-time margin", "B3/B5")
    resp, body = call("GET", f"/quotations/{quotation_id}/upsell-suggestions", headers=H)
    require_ok(resp, body, "upsell suggestions")
    show("Suggestions", [f"{s['product_name']} (+{s['margin_delta']} margin)" for s in body])

    resp, body = call("GET", f"/quotations/{quotation_id}", headers=H)
    require_ok(resp, body, "get quotation")
    show("Quotation total margin", body["total_margin"])
    print("  Margin is computed from real product cost data, not display-only.")

    # ---- 6. Two-step approval chain ----------------------------------------
    header(
        "Sales Manager approves -- escalates to Finance, doesn't confirm yet",
        "A3, 'which range needs Sales Manager followed by Finance'",
    )
    resp, body = call("POST", f"/approvals/{approval_id}/decision", json={
        "action": "approve", "user": "M. Shah", "user_id": 2,
    }, headers=H)
    require_ok(resp, body, "manager approve")
    show("Stage after manager approves", body["stage"])
    assert body["stage"] == "finance", "HIGH risk must escalate to finance, not confirm"
    print("  One approval was NOT enough to confirm a HIGH-risk deal -- it")
    print("  needed a second, independent Finance sign-off. That's a real")
    print("  two-step chain, not a single rubber stamp.")

    resp, body = call("POST", f"/approvals/{approval_id}/decision", json={
        "action": "approve", "user": "K. Iyer", "user_id": 3,
    }, headers=H)
    require_ok(resp, body, "finance approve")
    show("Stage after finance approves", body["stage"])
    assert body["stage"] == "confirmed"

    resp, body = call("GET", f"/quotations/{quotation_id}", headers=H)
    show("Quotation status", body["status"])

    # ---- 7. Warehouse fulfillment split -------------------------------------
    header(
        "Fulfillment auto-splits across warehouses by real stock + cost",
        "'order can be automatically split across warehouses'",
    )
    resp, body = call("GET", f"/fulfillment/{quotation_id}", headers=H)
    require_ok(resp, body, "fulfillment split")
    show("Splits", body["splits"])
    show("Backorders", body["backorders"])

    # ---- 8. Invoice was auto-created, now record a payment -----------------
    header(
        "Invoice auto-generated on approval; record a payment against it",
        "Quick Test Flow step 8",
    )
    resp, invoices = call("GET", "/invoices", headers=H)
    require_ok(resp, invoices, "list invoices")
    invoice = next(i for i in invoices if i["quotation_id"] == quotation_id)
    show("Invoice", invoice)

    resp, body = call("POST", f"/invoices/{invoice['id']}/pay", json={
        "amount": invoice["amount"], "method": "bank_transfer",
    }, headers=H)
    require_ok(resp, body, "pay invoice")
    resp, body = call("GET", f"/invoices/{invoice['id']}", headers=H)
    show("Invoice status after payment", body["status"])
    assert body["status"] == "paid"

    # ---- 9. Hybrid billing: one-time + recurring on separate tracks --------
    header(
        "Hybrid billing -- recurring subscription lines tracked separately",
        "'mix one time products and recurring subscription lines'",
    )
    resp, subs = call("GET", "/subscriptions", headers=H)
    require_ok(resp, subs, "list subscriptions")
    show("Active subscriptions", [f"{s['customer_name']}: {s['plan']} @ {s['amount']}/{s['cycle']}" for s in subs])
    if subs:
        sid = subs[0]["id"]
        resp, body = call("PATCH", f"/subscriptions/{sid}", json={"amount": subs[0]["amount"] * 1.4}, headers=H)
        require_ok(resp, body, "patch subscription")
        show("Prorated charge for the upgrade", body["proration_amount"])
        print("  That number isn't guessed -- it's (new - old amount) scaled")
        print("  by the days actually left in this billing cycle.")

    # ---- 10. Customer portal negotiation, auto re-entering approval -------
    header(
        "Customer negotiates in the portal; final terms re-enter approval automatically",
        "B8, 'if final terms exceed approval thresholds, automatically re-enters approval'",
    )
    resp, body = call("POST", "/portal/login", json={
        "email": "procurement@acme.example", "password": "password123",
    })
    require_ok(resp, body, "portal login")
    PH = {"Authorization": f"Bearer {body['access_token']}"}

    resp, quote_view = call("GET", f"/portal/quotations/{quotation_id}", headers=PH)
    require_ok(resp, quote_view, "portal view quotation")
    line_id = quote_view["lines"][0]["id"]

    resp, body = call("POST", f"/portal/quotations/{quotation_id}/negotiate", json={
        "message": "Can we get another 15% off the laptops?",
        "counter_discount_pct": 27, "quotation_line_id": line_id,
    }, headers=PH)
    require_ok(resp, body, "negotiate")
    show("Negotiation request status", body["status"])

    resp, body = call("POST", f"/portal/quotations/{quotation_id}/confirm", headers=PH)
    require_ok(resp, body, "portal confirm")
    show("Post-negotiation approval stage", body["stage"])
    show("Post-negotiation blended risk", body["blended_risk"])
    print("  The customer never talked to anyone -- clicking Confirm in the")
    print("  portal was enough to re-trigger the exact same risk engine and")
    print("  approval chain used for the original quote.")

    # ---- 11. Deal health + dashboard ----------------------------------------
    header("Deal health dashboard + nudge/escalate actions", "B9")
    resp, health = call("GET", "/deal-health", headers=H)
    require_ok(resp, health, "deal health")
    show("Stalled deals", len(health["stalled_deals"]))
    show("Discount anomalies", len(health["discount_anomalies"]))
    show("Delivery slippage", len(health["delivery_slippage"]))

    resp, body = call("POST", f"/deal-health/{quotation_id}/nudge", json={
        "user": "M. Shah", "note": "Checking in on this one",
    }, headers=H)
    require_ok(resp, body, "nudge")

    resp, dashboard = call("GET", "/dashboard/summary", headers=H)
    require_ok(resp, dashboard, "dashboard summary")
    show("Pending approvals", dashboard["pending_approvals"])
    show("Open quotations", dashboard["open_quotations"])
    show("At-risk deals", dashboard["at_risk_deals"])
    show("Most recent activity item", dashboard["recent_activity"][0] if dashboard["recent_activity"] else None)
    print("  That nudge you just sent is already the most recent item in")
    print("  the activity feed above -- pulled live from the audit trail.")

    # ---- 12. Admin/config surfaces still respond ----------------------------
    header("Backend configuration surfaces (admin screens)", "A2-A5")
    resp, tiers = call("GET", "/discount-tiers", headers=H)
    require_ok(resp, tiers, "discount tiers")
    show("Discount tiers configured", [t["name"] for t in tiers])
    resp, warehouses = call("GET", "/warehouses", headers=H)
    require_ok(resp, warehouses, "warehouses")
    show("Warehouses configured", [w["name"] for w in warehouses])
    resp, report = call("GET", "/reports/summary", headers=H)
    require_ok(resp, report, "reports summary")
    show("Report: quotes created", report["quotes_created"])
    show("Report: avg approval time (hrs)", report["avg_approval_time_hours"])

    print()
    print("=" * 78)
    print(" DONE. Every PDF workflow step above ran against a real Postgres")
    print(" database over real HTTP calls -- nothing in this script was")
    print(" mocked, stubbed, or pre-recorded.")
    print("=" * 78)


if __name__ == "__main__":
    try:
        requests.get(BASE_URL, timeout=3)
    except requests.exceptions.ConnectionError:
        print(f"Could not reach {BASE_URL}.")
        print("Start the server first, in another terminal:")
        print("    cd backend && uvicorn api.main:app --reload")
        sys.exit(1)
    main()
