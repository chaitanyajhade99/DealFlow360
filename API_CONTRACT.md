## Entities
- Quotation: id, customer_name, customer_tier, status, created_at, sales_rep_id (nullable FK -> users.id, added 2026-09-05), expected_delivery_date (nullable, added 2026-09-05), actual_delivery_date (nullable, added 2026-09-05)
- QuotationLine: id, quotation_id, product_id, category, qty, unit_price, discount_pct, category_limit_pct
- Approval: id, quotation_id, blended_risk (LOW/MEDIUM/HIGH), stage, assigned_to, history[]
  <!-- history[] entries now include a {"action": "flagged", "reason": ...} entry from
       score_risk()'s "reason" field, appended on every POST /quotations/{id}/submit. -->
- Warehouse: id, name, stock[{product_id, qty}], shipping_cost_per_unit, shipment_fixed_cost (added 2026-09-05)
- FulfillmentSplit: id, quotation_id, splits[{warehouse_id, qty, cost}]
  <!-- Rows where engines.split_warehouse() marks is_backorder=true are filtered out before
       persisting to splits[] -- they're returned transiently as `backorders` in the API
       response only (GET /fulfillment/{id}), never written to this table. -->
- Subscription: id, customer_name, plan, cycle, next_bill_date, status
- Invoice: id, quotation_id, amount, status, due_date
- DiscountTier: id, name (Bronze/Silver/Gold), max_discount_pct, category_limits{category: pct}, approval_chain{LOW/MEDIUM/HIGH: stage}
  <!-- Added 2026-09-05: backs PDF section A3 / wireframe screen 18 ("Discount tiers
       and approval chains"). One row per tier holds the tier ceiling, the
       per-category ceilings, and the risk->approval-stage routing, since the
       wireframe combines all three into a single config screen. -->

- User: id, name, email, password_hash, role (sales_rep/sales_manager/finance/admin), created_at, seniority (nullable smallint: 0 junior/1 mid/2 principal, added 2026-09-05)
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
     deliberately deferred -- see the reports section below. -->

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

### Approvals
POST /approvals/{id}/decision         -> approve/reject/return; auto-creates an Invoice
                                          when the chain fully clears

### Fulfillment
GET /fulfillment/{quotation_id}       -> calls engines.split_warehouse()

### Auth (internal users) -- added 2026-09-05
POST /auth/signup
POST /auth/login                      -> returns a JWT (type: "internal")

### Customer portal -- added 2026-09-05, PDF B8
<!-- Restricted per section 7's Technical Guidelines: every route below except
     /portal/login and /portal/magic-link requires a customer-type JWT
     (Authorization: Bearer <token>), never an internal one. -->
POST /portal/login
POST /portal/magic-link               -> no email service wired up; returns the token
                                          directly instead of emailing it
GET /portal/quotations/{id}           -> restricted read; same margin/product_name fields
POST /portal/quotations/{id}/negotiate -> creates a NegotiationRequest, sets status "negotiation"
POST /portal/quotations/{id}/confirm  -> applies the latest pending counter_discount_pct to
                                          its line, then re-runs the same scoring path as
                                          POST /quotations/{id}/submit -- if final terms
                                          exceed thresholds it re-enters approval automatically

### Subscriptions
POST /subscriptions
GET /subscriptions                    -> added 2026-09-05
GET /subscriptions/{id}               -> added 2026-09-05
PATCH /subscriptions/{id}             -> added 2026-09-05; plan/cycle/status only --
                                          Subscription has no amount/qty field to prorate
                                          a mid-cycle charge against
POST /subscriptions/{id}/cancel       -> added 2026-09-05; optional refund_amount creates
                                          a CreditNote (amount is caller-supplied, not
                                          auto-prorated, for the same reason as above)
GET /subscriptions/{id}/credit-notes  -> added 2026-09-05
POST /subscription-plans              -> added 2026-09-05, PDF A5
GET /subscription-plans               -> added 2026-09-05

### Invoices / Payments
POST /invoices                        -> added 2026-09-05, manual/admin creation
GET /invoices
GET /invoices/{id}                    -> added 2026-09-05
POST /invoices/{id}/pay               -> added 2026-09-05; records a Payment, sets
                                          Invoice.status to "paid" once fully covered

### Deal health
GET /deal-health                      -> calls engines.detect_anomalies(); now also returns
                                          delivery_slippage[] (quotations past
                                          expected_delivery_date with no actual_delivery_date)

### Discount tiers
POST /discount-tiers
GET /discount-tiers
PATCH /discount-tiers/{id}

### Warehouses -- added 2026-09-05, PDF A4
POST /warehouses
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