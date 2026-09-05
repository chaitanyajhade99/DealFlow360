## Entities
- Quotation: id, customer_name, customer_tier, status, created_at, sales_rep_id (nullable FK -> users.id, added 2026-09-05), expected_delivery_date (nullable, added 2026-09-05), actual_delivery_date (nullable, added 2026-09-05)
- QuotationLine: id, quotation_id, product_id, category, qty, unit_price, discount_pct, category_limit_pct
- Approval: id, quotation_id, blended_risk (LOW/MEDIUM/HIGH), stage, assigned_to, history[], flagged_lines[] (added 2026-09-05)
  <!-- history[] entries now include a {"action": "flagged", "reason": ...} entry from
       score_risk()'s "reason" field, appended on every POST /quotations/{id}/submit.
       flagged_lines[] persists score_risk()'s per-line breakdown (line, discount_given_pct,
       limit_allowed_pct, over_by_pct, ...) so wireframe screen 6's "Why This Quote Was
       Flagged" table can be re-read later instead of being computed-and-discarded at
       submit time. -->
- Warehouse: id, name, stock[{product_id, qty}], shipping_cost_per_unit, shipment_fixed_cost (added 2026-09-05), replenishment_rules (json, added 2026-09-05, e.g. {"reorder_point": 10, "reorder_qty": 40} -- PDF A4)
- FulfillmentSplit: id, quotation_id, splits[{warehouse_id, qty, cost}]
  <!-- Rows where engines.split_warehouse() marks is_backorder=true are filtered out before
       persisting to splits[] -- they're returned transiently as `backorders` in the API
       response only (GET /fulfillment/{id}), never written to this table. -->
- Subscription: id, customer_name, plan, cycle, next_bill_date, status, amount (nullable, added 2026-09-05), qty (nullable, added 2026-09-05), quotation_id (nullable FK -> quotations.id, added 2026-09-05)
  <!-- amount/qty added so PDF B7's mid-cycle proration and cancellation refunds can be
       computed for real (amount * days_remaining_in_cycle / cycle_length_days) instead of
       requiring the caller to supply a manually-guessed refund_amount every time. Both stay
       nullable -- a subscription created without them just gets no auto-computed proration. -->
- Invoice: id, quotation_id, amount, status, due_date
- DiscountTier: id, name (Bronze/Silver/Gold), max_discount_pct, category_limits{category: pct}, approval_chain{LOW/MEDIUM/HIGH: stage}
  <!-- Added 2026-09-05: backs PDF section A3 / wireframe screen 18 ("Discount tiers
       and approval chains"). One row per tier holds the tier ceiling, the
       per-category ceilings, and the risk->approval-stage routing, since the
       wireframe combines all three into a single config screen. -->

- User: id, name, email, password_hash, role (sales_rep/sales_manager/finance/admin), created_at, seniority (nullable smallint: 0 junior/1 mid/2 principal, added 2026-09-05), status (pending/approved/rejected, added 2026-09-05, server default "approved" so pre-existing rows are unaffected -- new self-service signups start "pending" and cannot log in until an Admin approves them)
- Customer: id, name, default_tier, created_at
- CustomerUser: id, customer_id, email, password_hash (nullable), auth_method (password/magic_link), created_at
- Product: id, product_code, name, category, price, unit, tax_pct, description, is_subscription, recurring_cycle, quantity_on_hand, cost (nullable, added 2026-09-05), is_promoted (added 2026-09-05), promo_tag (nullable, added 2026-09-05)
- ProductVariant: id, product_id, attribute, value, extra_price
- PriceList: id, product_id, customer_tier, currency, price_rule (json)
- SubscriptionPlan: id, name, cycle, proration_rule (json), cancellation_rule (json)
- UpsellRule: id, source_product_id, suggested_product_id, is_promoted, min_margin_pct
- AuditLog: id, entity_type, entity_id, user_id (nullable), action, reason (nullable), before (json), after (json), created_at
- Payment: id, invoice_id, amount, method, paid_at
- CreditNote: id, subscription_id (nullable), invoice_id (nullable), amount, reason, created_at
- NegotiationRequest: id, quotation_id, quotation_line_id (nullable), customer_user_id (nullable), message, counter_discount_pct (nullable), status (pending/resolved), created_at

## Endpoints (Person 1 owns implementation)

<!-- Full gap-closure pass, 2026-09-05: went from 12 to 41 endpoints. Every
     PDF section now has a backing endpoint except PDF/XLS export (A7),
     deliberately deferred -- see the reports section below.

     Frontend-integration hardening pass, 2026-09-05 (second pass same day):
       - CORS is now enabled (CORSMiddleware, all origins by default -- set
         CORS_ORIGINS env var to a comma-separated allowlist for deployment).
       - EVERY endpoint below except POST /auth/signup, POST /auth/login, and
         everything under /portal/* now REQUIRES `Authorization: Bearer <token>`
         from POST /auth/login (an internal-type JWT). A request without one
         gets 401; a customer-type (/portal) token gets 403. This was
         previously scoped out to avoid breaking in-progress frontend calls --
         since no frontend existed yet, it's closed now rather than left as a
         known gap going into integration.
       - Added GET /approvals, GET /approvals/{id} (wireframe screens 5/6 had
         no way to list or fetch an approval before this).
       - Added GET /dashboard/summary (wireframe screen 2).
       - Added POST /deal-health/{quotation_id}/nudge and /escalate (PDF B9).
       - PATCH /subscriptions/{id} response shape changed -- see below.

     Full frontend integration pass, 2026-09-05 (third pass same day): the
     React frontend (frontend/src) is now wired end-to-end to every endpoint
     below -- no mock data, no local-only write stubs. Added GET /portal/me,
     GET /portal/quotations (list), GET /portal/negotiations, and a
     quotation_id/status filter on GET /subscriptions to support it. Fixed a
     real security gap in the process: /portal/quotations/{id} (and
     negotiate/confirm) now verify the quotation's customer_name matches the
     caller's own Customer record before returning/mutating anything.

     Feature-completion pass, 2026-09-05 (fourth pass same day): closed the
     remaining PDF gaps raised in review --
       - POST /auth/signup now creates status="pending" accounts restricted to
         sales_rep/sales_manager/finance (admin cannot self-signup); POST
         /auth/login now rejects pending/rejected accounts with 403. New
         GET/POST /admin/users* routes (below) let an Admin approve or reject
         them.
       - POST /portal/signup lets a customer self-register and link to (or
         create) their Customer org without needing an internal user to set
         one up first -- auto-approved, no admin gate (unlike internal signup)
         since it would otherwise block a rep's very first quote to a new
         account.
       - GET /quotations/{id}/pdf generates a real PDF (reportlab) of the
         quotation's line items and totals, streamed on demand -- not cached.
       - POST /invoices/{id}/razorpay-order and POST
         /invoices/{id}/razorpay-verify add a real Razorpay Checkout (test
         mode) payment path alongside the existing manual POST
         /invoices/{id}/pay; verify checks the HMAC-SHA256 signature
         server-side before marking the invoice paid. -->

### Quotations
POST /quotations                      -> sales_rep_id and expected_delivery_date optional
GET /quotations                       -> each line carries transient product_name + margin;
                                          quotation carries transient total_margin (PDF B3)
GET /quotations/{id}
PATCH /quotations/{id}/lines          -> category_limit_pct optional (auto-filled from
                                          DiscountTier); logs an AuditLog "edit" entry
                                          (optional edited_by_user_id + reason in body)
POST /quotations/{id}/submit          -> calls engines.score_risk() with context (see below);
                                          result["reason"] appended into Approval.history;
                                          auto-creates an Invoice if no approval was needed
GET /quotations/{id}/upsell-suggestions -> calls engines.recommend_upsell() (PDF B5)
GET /quotations/{id}/pdf              -> added 2026-09-05; streams a generated PDF
                                          (application/pdf) of the quotation's line items,
                                          discounts, and total -- built with reportlab,
                                          not persisted/cached

### Approvals
GET /approvals                        -> added 2026-09-05; ?pending_only=true filters to
                                          stage in (sales_manager, finance) -- screen 5
GET /approvals/{id}                   -> added 2026-09-05; includes flagged_lines[]
                                          (screen 6's "Why This Quote Was Flagged" table)
POST /approvals/{id}/decision         -> approve/reject/return; auto-creates an Invoice
                                          when the chain fully clears; now also writes an
                                          AuditLog "approval" entry (added 2026-09-05)

### Fulfillment
GET /fulfillment/{quotation_id}       -> calls engines.split_warehouse()

### Auth (internal users) -- added 2026-09-05
POST /auth/signup                     -> role must be sales_rep/sales_manager/finance (admin
                                          rejected with 400); creates status="pending" --
                                          cannot log in until an Admin approves (see /admin/users)
POST /auth/login                      -> returns a JWT (type: "internal"); 403 if the account
                                          is still "pending" or was "rejected"

### Admin -- added 2026-09-05
<!-- All routes require an internal JWT AND role == "admin" (403 otherwise). -->
GET /admin/users                      -> ?status=pending|approved|rejected filter
POST /admin/users/{id}/approve        -> sets status="approved"
POST /admin/users/{id}/reject         -> sets status="rejected"

### Customer portal -- added 2026-09-05, PDF B8
<!-- Restricted per section 7's Technical Guidelines: every route below except
     /portal/login and /portal/magic-link requires a customer-type JWT
     (Authorization: Bearer <token>), never an internal one. -->
POST /portal/signup                   -> added 2026-09-05; self-service, no admin approval.
                                          Reuses an existing Customer row matched by
                                          company_name, or creates one -- so a rep's earlier
                                          quotation against that name resolves to this account
POST /portal/login
POST /portal/magic-link               -> no email service wired up; returns the token
                                          directly instead of emailing it
GET /portal/me                        -> added 2026-09-05, frontend-integration pass;
                                          {customer_user, customer} for the logged-in account
GET /portal/quotations                -> added 2026-09-05; every quotation whose
                                          customer_name matches this account's Customer.name
GET /portal/negotiations              -> added 2026-09-05; this account's NegotiationRequests
                                          across all of its quotations, newest first
GET /portal/quotations/{id}           -> restricted read; same margin/product_name fields.
                                          Ownership-checked (2026-09-05 fix): 404s if the
                                          quotation's customer_name doesn't match the caller's
                                          account -- previously any valid customer token could
                                          read/negotiate on any quotation by guessing an id
POST /portal/quotations/{id}/negotiate -> creates a NegotiationRequest, sets status "negotiation"
POST /portal/quotations/{id}/confirm  -> applies the latest pending counter_discount_pct to
                                          its line, then re-runs the same scoring path as
                                          POST /quotations/{id}/submit -- if final terms
                                          exceed thresholds it re-enters approval automatically

### Subscriptions
POST /subscriptions
GET /subscriptions                    -> added 2026-09-05; ?quotation_id= and ?status= filters
                                          added in the frontend-integration pass
GET /subscriptions/{id}               -> added 2026-09-05
PATCH /subscriptions/{id}             -> added 2026-09-05; now accepts amount/qty too.
                                          Response shape changed same day:
                                          {subscription, proration_amount, credit_note}.
                                          proration_amount = (new_amount - old_amount) *
                                          (days_remaining_in_cycle / cycle_length_days);
                                          negative values auto-create a CreditNote
                                          (returned in credit_note), positive values are
                                          reported but NOT auto-invoiced -- raise that
                                          manually via POST /invoices
POST /subscriptions/{id}/cancel       -> added 2026-09-05; refund_amount is now optional --
                                          when omitted and the subscription has amount +
                                          next_bill_date set, it's auto-computed the same
                                          way as the PATCH proration above; still
                                          overridable by passing refund_amount explicitly
GET /subscriptions/{id}/credit-notes  -> added 2026-09-05
POST /subscription-plans              -> added 2026-09-05, PDF A5
GET /subscription-plans               -> added 2026-09-05

### Invoices / Payments
POST /invoices                        -> added 2026-09-05, manual/admin creation
GET /invoices
GET /invoices/{id}                    -> added 2026-09-05
POST /invoices/{id}/pay               -> added 2026-09-05; records a Payment, sets
                                          Invoice.status to "paid" once fully covered
POST /invoices/{id}/razorpay-order    -> added 2026-09-05; creates a Razorpay order
                                          (TEST mode) server-side for invoice.amount in
                                          paise, returns {order_id, amount, currency, key_id}
                                          for the frontend to open Checkout with
POST /invoices/{id}/razorpay-verify   -> added 2026-09-05; verifies Checkout's
                                          HMAC-SHA256 signature server-side (never trusts the
                                          client-side success callback alone), then records a
                                          Payment (method="razorpay") and marks the invoice paid

### Deal health
GET /deal-health                      -> calls engines.detect_anomalies(); now also returns
                                          delivery_slippage[] (quotations past
                                          expected_delivery_date with no actual_delivery_date)
POST /deal-health/{quotation_id}/nudge    -> added 2026-09-05, PDF B9's "automated nudge ...
                                              action ... triggered from an alert"; writes an
                                              AuditLog entry, shows up in dashboard activity
POST /deal-health/{quotation_id}/escalate -> added 2026-09-05, same as nudge but for
                                              "escalation"; body: {user?, note?}

### Dashboard -- added 2026-09-05, PDF wireframe screen 2
GET /dashboard/summary                -> {pending_approvals, open_quotations, at_risk_deals,
                                          recent_activity[]}. recent_activity merges
                                          AuditLog + Approval.history + NegotiationRequest,
                                          newest first; ?activity_limit=N (default 10, max 50)

### Discount tiers
POST /discount-tiers
GET /discount-tiers
PATCH /discount-tiers/{id}

### Warehouses -- added 2026-09-05, PDF A4
POST /warehouses                      -> accepts replenishment_rules (json, e.g.
                                          {"reorder_point": 10, "reorder_qty": 40})
GET /warehouses
GET /warehouses/{id}
PATCH /warehouses/{id}

### Products -- added 2026-09-05, PDF A2
POST /products                        -> accepts nested variants[] and price_lists[]
GET /products
GET /products/{id}
PATCH /products/{id}

### Reports -- added 2026-09-05, PDF A7
GET /reports/summary                  -> filters: date_from, date_to, sales_rep_id,
                                          approval_status, category. Returns quotes_created,
                                          avg_approval_time_hours, top_discounted_product,
                                          matching_quotations[].
                                          PDF/XLS export is NOT implemented -- deferred,
                                          needs a library decision (reportlab/openpyxl)

## Engine function signatures (Person 2 owns implementation, pure functions, no DB access)
<!-- Updated 2026-09-05: score_risk gained 4 optional context params + a required
     "reason" key in its return (plain-language explanation, stored in Approval.history).
     split_warehouse's return rows gained "is_backorder" -- Person 1 filters those out
     before persisting FulfillmentSplit.splits[] and returns them separately as
     `backorders` in the GET /fulfillment/{id} response. -->
score_risk(
    lines: list[dict],
    customer_tier: str | None = None,
    rep_avg_discount_pct: float | None = None,
    is_quarter_end: bool = False,
    seniority: int | None = None,
) -> {blended_risk: str, flagged_lines: list[dict], reason: str}
split_warehouse(product_id: str, qty: int, warehouses: list[dict]) -> list[{warehouse_id, qty, cost, is_backorder: bool}]
  <!-- warehouses dicts now include shipping_cost_per_unit and shipment_fixed_cost
       (from the Warehouse table) alongside id/name/stock, for real cost computation. -->
detect_anomalies(rep_discount_history: list[float], current_discount: float) -> {is_anomaly: bool, z_score: float}
recommend_upsell(cart_items: list[str], co_occurrence_data: dict) -> list[{product_id, margin_delta}]