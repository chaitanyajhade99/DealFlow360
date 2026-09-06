## Production-readiness pass -- 2026-09-06

Full audit + fix cycle against the PS/Excalidraw. Summary (see inline changelogs
at each affected entity/endpoint for detail):

- **RBAC enforced server-side, not just hidden in the frontend.** Added
  `api.deps.require_roles()`. `POST/PATCH /products`, `/discount-tiers`,
  `/warehouses`, `/subscription-plans` are now Admin-only (discount-tiers also
  allows Sales Manager, per PS section 3 giving both roles that
  responsibility). `POST /approvals/{id}/decision` now requires
  `sales_manager`/`admin` at the sales_manager stage and `finance`/`admin` at
  the finance stage -- a Sales Rep can no longer approve their own quotation.
  `POST /invoices/{id}/pay` is Finance/Admin-only.
- **State-machine integrity**: `PATCH /quotations/{id}/lines` now rejects
  (400) editing a quotation whose status isn't `draft`/`negotiation` --
  previously a confirmed/approved quotation (with an invoice already raised
  off its numbers) could still be silently rewritten via direct API call.
  `POST /approvals/{id}/decision` also now rejects re-deciding an
  already-resolved approval (blocks a double-click/replay double-processing
  the same decision).
- **Payment integrity**: both the Finance manual-reconciliation endpoint and
  the customer Razorpay-verify endpoint now row-lock the invoice
  (`SELECT ... FOR UPDATE`) and reject a) paying an already-`paid` invoice,
  b) a non-positive amount, c) an amount exceeding the remaining balance --
  closing a real double-payment/overpayment race.
- **Hybrid billing wired for real (PDF B7)**: confirming/approving a
  quotation with Subscription-category lines now creates an actual
  `Subscription` row (correct cycle, recurring amount, next bill date) via
  `_create_subscriptions_if_needed()`, called from the same
  `create_invoice_if_needed()` choke point both auto-confirm and
  manager/finance-cleared approval already funnel through. The one-time
  invoice total now excludes Subscription-category lines (previously they
  were double-counted: once in the flat invoice, and never in any recurring
  record at all, since nothing ever created one).
- **Price Lists actually applied (PDF A2)**: `_resolve_unit_price()` now
  checks for a tier-specific `PriceList` override (`fixed` or `markup_pct`)
  before falling back to `Product.price`. Previously this table was
  write-only -- configurable in the admin screen but never read.
- **Fulfillment Manual Override implemented (PDF B6)**: previously a
  frontend-only local preview with an honest "no write endpoint" disclaimer.
  See `POST/GET/reset /fulfillment/{quotation_id}` below.
- **ML risk-escalation layer activated**: `xgboost` and `openpyxl` were
  missing from the environment entirely (not even in `requirements.txt`), so
  `engines/risk_engine.py`'s trained model artifact silently never loaded and
  every score was rules-only. Both are now installed and declared; the model
  layer is confirmed live (`model_available: true`).
- **Reports export (PDF/XLS) implemented** -- `GET /reports/export.pdf` and
  `GET /reports/export.xlsx`, sharing the exact filter/aggregation function
  `GET /reports/summary` itself uses, so the downloaded file and the on-screen
  numbers can never drift apart.
- **New automated test suite**: `backend/tests/test_production_readiness.py`
  (23 tests, `pytest`) -- there was no API-level test coverage before this
  pass, only the pure-function `engines/tests/` suite (106 tests, untouched,
  still green). Runs against the real configured DB, not an isolated test
  DB; see the file's own docstring for that tradeoff.
- **Read-access RBAC, not just mutations**: a first pass gated only writes
  (config, approvals, payments). On review, PS section 3 explicitly assigns
  warehouse fulfillment management and billing reconciliation to
  Finance/Operations, not the Sales Rep -- so `GET /warehouses`,
  `GET /invoices`, `GET /invoices/{id}` are now Finance/Admin-only reads too,
  and `POST /fulfillment/{id}/override|reset` (added earlier in this same
  pass) moved from open-to-any-internal-role to Finance/Admin-only, matching
  that same assignment. `GET /fulfillment/{id}` itself stays open to every
  internal role -- a rep "tracks fulfillment progress" (PS section 3), which
  is read access, just not the override decision.
- **Fixed a latent session bug this surfaced**: the frontend's `request()`
  helper treated any `403` exactly like a `401` and cleared the entire
  session -- meaning a Sales Rep merely viewing a screen that makes one
  now-role-gated call (e.g. Fulfillment fetching `/warehouses`) would have
  been silently logged out. `403` now surfaces as an ordinary per-call error;
  only `401` (an actually-invalid/expired token) drops the session.

## Entities
- Quotation: id, customer_name, customer_tier, status, created_at, sales_rep_id (nullable FK -> users.id, added 2026-09-05), expected_delivery_date (nullable, added 2026-09-05), actual_delivery_date (nullable, added 2026-09-05)
- QuotationLine: id, quotation_id, product_id, category, qty, unit_price, discount_pct, category_limit_pct
  <!-- Changelog 2026-09-06: unit_price and category are now server-resolved from the
       matching Product record on POST /quotations and PATCH /quotations/{id}/lines --
       whatever the client sends for these two fields is discarded, not persisted. Per
       PDF A2/B3, price is backend-configured (price lists), and the rep's only lever
       on a line is qty/discount_pct; trusting a client-sent unit_price would let a rep
       dodge the blended discount risk engine entirely by lowering "price" instead of
       taking a discount that would trigger approval. -->
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
- UpsellRule: id, source_product_id, suggested_product_id, is_promoted, min_margin_pct, suggestion_type ("upsell" | "cross_sell", default "cross_sell", added 2026-09-06 -- see DATABASE_SCHEMA.md #16)
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
         server-side before marking the invoice paid.

     Business-logic pass, 2026-09-06:
       - Currency switched from USD to INR everywhere (display formatting,
         PriceList.currency default, the quotation PDF's amounts).
       - New GET/POST /customers -- the quotation builder now picks an
         existing customer from this list instead of a Sales Rep typing a
         free-text name/tier; tier always rides along from the selected
         Customer.default_tier and is never manually entered (see
         api.tiering -- it's earned from closed order volume, same rule as
         portal signups).
       - Razorpay moved from /invoices/* (internal) to /portal/invoices/*
         (customer-only, ownership-checked): the internal workspace no
         longer has any route that can trigger or complete a real payment.
         POST /invoices/{id}/razorpay-order and /razorpay-verify are
         REMOVED; POST /invoices/{id}/pay remains, but is now documented as
         Finance's manual/offline-reconciliation path only -- the customer
         is the only party who can pay an invoice through a real gateway. -->

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
GET /quotations/{id}/negotiations     -> added 2026-09-06; every NegotiationRequest for this
                                          quotation, newest first. Backs a rep-facing panel --
                                          previously a submitted negotiation only surfaced as a
                                          line in the dashboard's generic activity feed, with no
                                          screen where the rep could see the actual message/
                                          counter or act on it (gap vs PDF section 3: "Sales
                                          Rep ... Responds to customer negotiation requests").
POST /quotations/{id}/negotiations/{negotiation_id}/respond -> added 2026-09-06.
                                          {action: "accept"|"decline", note?}. "accept" applies
                                          counter_discount_pct to its line and re-runs
                                          score_and_route() -- same path as the customer's own
                                          "Confirm Quotation", so a rep-accepted counter is held
                                          to the same approval thresholds and can itself route
                                          to Sales Manager/Finance if it's now too aggressive.
                                          "decline" resolves the request with no pricing change
                                          and drops the quotation back to "draft" once no other
                                          negotiation request is still pending on it.
GET /quotations/{id}/upsell-suggestions -> calls engines.recommend_upsell() (PDF B5).
                                          Fixed 2026-09-06: this route used to pass the
                                          engine no real "margin" key (only an unused
                                          min_margin_pct), so every call silently degraded
                                          to a likelihood-only ranking (margin_delta/score
                                          always 0). Now computes real margin (price - cost)
                                          per suggestion and a real co_purchase_count from
                                          actual historical QuotationLine co-occurrence, so
                                          ranking_basis is genuinely "count_x_margin"/
                                          "confidence_x_margin" instead of always degrading.
GET /quotations/{id}/pdf              -> added 2026-09-05; streams a generated PDF
                                          (application/pdf) of the quotation's line items,
                                          discounts, and total -- built with reportlab,
                                          not persisted/cached.
                                          Query param `preview` (bool, default false, added
                                          2026-09-06): when true, Content-Disposition is
                                          "inline" instead of "attachment" (opens in-browser
                                          instead of downloading), and the PDF gains a
                                          "Governance & Risk Review" section built from the
                                          quotation's latest Approval -- blended_risk, stage,
                                          the same flagged-lines breakdown shown on the
                                          Approval screen, and reviewer notes from
                                          approval.history. Lets a Sales Manager/Finance
                                          reviewer open one document that shows both the full
                                          quotation and why it was flagged, instead of
                                          cross-referencing two screens.

### Approvals
GET /approvals                        -> added 2026-09-05; ?pending_only=true filters to
                                          stage in (sales_manager, finance) -- screen 5
GET /approvals/{id}                   -> added 2026-09-05; includes flagged_lines[]
                                          (screen 6's "Why This Quote Was Flagged" table)
POST /approvals/{id}/decision         -> approve/reject/return; auto-creates an Invoice
                                          when the chain fully clears; now also writes an
                                          AuditLog "approval" entry (added 2026-09-05).
                                          Changelog 2026-09-06: the reviewer recorded in
                                          history/AuditLog is now resolved server-side from
                                          the caller's JWT (api.deps.get_current_internal_user),
                                          not the request body -- the request no longer takes
                                          `user`/`user_id` at all. Previously the frontend sent
                                          a hardcoded literal "Current User" string for every
                                          decision regardless of who was actually logged in,
                                          and nothing stopped a client from claiming to be
                                          anyone. Same fix applied to POST
                                          /deal-health/{id}/nudge and /escalate below.

### Quotation integrity -- added 2026-09-06
<!-- POST /quotations and PATCH /quotations/{id}/lines both now reject a
     payload with zero lines carrying a non-empty product_id and qty > 0
     (400 "A quotation needs at least one line item..."). Previously a
     quotation (or an edit) with an empty cart silently persisted. -->

### Fulfillment
GET /fulfillment/{quotation_id}       -> calls engines.split_warehouse(). Changelog
                                          2026-09-06: no longer unconditionally recomputes/
                                          overwrites splits -- if FulfillmentSplit.is_manual_override
                                          is true (see POST .../override below), the persisted
                                          split is returned as-is with backorders recomputed
                                          against it, instead of being silently clobbered by a
                                          fresh auto-suggestion on every GET.
POST /fulfillment/{quotation_id}/override -> added 2026-09-06. PDF B6's "Manual Override",
                                          previously a frontend-only local preview with no
                                          write endpoint. Body: list of
                                          {product_id, warehouse_id, qty}. Validates every
                                          allocation against that warehouse's real live stock
                                          and rejects allocating more than a line's own
                                          required qty (400 either way); under-allocating a
                                          line is allowed and produces a real backorder entry,
                                          same shape as the auto engine's. Persists with
                                          is_manual_override=true.
POST /fulfillment/{quotation_id}/reset -> added 2026-09-06. "Accept Suggested Split" --
                                          clears is_manual_override so the next GET goes back
                                          to the live auto-allocation engine.

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
GET /admin/customers                  -> added 2026-09-06; ?status=pending|approved|rejected
                                          filter -- the Customer Approvals queue
POST /admin/customers/{id}/approve    -> added 2026-09-06; sets Customer.status="approved" --
                                          the company then appears in GET /customers (below)
                                          and its portal users can log in
POST /admin/customers/{id}/reject     -> added 2026-09-06; sets Customer.status="rejected"

### Customers -- added 2026-09-06
<!-- Any internal user (not admin-gated) -- a Sales Rep must be able to
     onboard a brand-new company before quoting them. -->
GET /customers                        -> list, ordered by name; backs the quotation
                                          builder's customer picker (name + tier both
                                          come from here, never typed free-text).
                                          Defaults to ?status=approved -- a company
                                          still pending Admin approval (see
                                          /admin/customers above) never appears here,
                                          which is what actually keeps it out of the
                                          quotation builder until approved. Pass
                                          ?status=all or a specific value to override.
POST /customers                       -> {name} only; always starts default_tier="Bronze"
                                          AND status="approved" -- an internal user is
                                          vouching for it, unlike self-service portal
                                          signup below, which starts "pending"

### Customer portal -- added 2026-09-05, PDF B8
<!-- Restricted per section 7's Technical Guidelines: every route below except
     /portal/login and /portal/magic-link requires a customer-type JWT
     (Authorization: Bearer <token>), never an internal one. -->
POST /portal/signup                   -> added 2026-09-05; reuses an existing Customer row
                                          matched by company_name, or creates one -- so a
                                          rep's earlier quotation against that name resolves
                                          to this account. Business-logic change 2026-09-06:
                                          a brand-new company now starts Customer.status=
                                          "pending" and this endpoint returns {status:
                                          "pending", access_token: null} -- no usable token
                                          until an Admin approves (see /admin/customers).
                                          Signing up as an additional contact for an
                                          already-"approved" company skips the wait and
                                          returns {status: "approved", access_token: "..."}
                                          immediately, since the org itself is already vetted.
POST /portal/login                    -> 403 "awaiting admin approval"/"rejected" (added
                                          2026-09-06) if the account's Customer.status isn't
                                          "approved" -- mirrors internal /auth/login's gate
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
POST /portal/quotations/{id}/negotiate -> creates a NegotiationRequest, sets status "negotiation".
                                          Changelog 2026-09-06: when counter_discount_pct is
                                          sent, it's rejected (400) unless it's strictly higher
                                          than that line's current discount_pct (and <=100) --
                                          enforced server-side, not just in the UI, since this
                                          is a customer-JWT route a scripted request could hit
                                          directly. A counter that isn't higher than what's
                                          already offered isn't a counter-offer.
POST /portal/quotations/{id}/confirm  -> applies the latest pending counter_discount_pct to
                                          its line, then re-runs the same scoring path as
                                          POST /quotations/{id}/submit -- if final terms
                                          exceed thresholds it re-enters approval automatically
GET /portal/quotations/{id}/pdf       -> added 2026-09-06; customer-facing equivalent of
                                          GET /quotations/{id}/pdf, ownership-checked. Always
                                          opens inline (preview). Shares build_quotation_pdf()
                                          with the internal route but with
                                          include_governance=False -- the internal risk-score/
                                          flagged-lines/reviewer-notes section never appears on
                                          a customer's copy.
GET /portal/invoices                  -> added 2026-09-06; every invoice raised against this
                                          account's own quotations
GET /portal/invoices/{id}             -> added 2026-09-06; ownership-checked like quotations
POST /portal/invoices/{id}/razorpay-order   -> added 2026-09-06 (moved here from the
                                          internal /invoices/* -- see business-logic pass
                                          note above); creates a Razorpay order server-side
POST /portal/invoices/{id}/razorpay-verify  -> added 2026-09-06; verifies the HMAC-SHA256
                                          signature server-side, then marks the invoice paid.
                                          This pair is now the ONLY way an invoice gets paid
                                          through a real payment gateway -- the customer pays
                                          their own invoice, the internal workspace cannot

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
POST /invoices/{id}/pay               -> added 2026-09-05; Finance-only MANUAL/offline
                                          reconciliation (e.g. an already-received bank
                                          transfer) -- NOT a real payment gateway. Real
                                          online payment moved to POST
                                          /portal/invoices/{id}/razorpay-order|verify
                                          (2026-09-06 business-logic pass): the customer pays
                                          their own invoice through the portal; this endpoint
                                          just lets Finance mark one paid when money genuinely
                                          arrived some other way

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