# DealFlow360 — Database Schema (for frontend integration)

Owner: Person 1 (backend/models, backend/api, backend/seed). Source of truth
for field names/types is `API_CONTRACT.md`; this doc adds the detail frontend
needs — actual column types, JSON shapes, enum conventions, and relationships
— that the one-line contract entries don't spell out.

Postgres, accessed via SQLAlchemy. All primary keys are auto-incrementing
integers. All endpoints are documented live at `/docs` (Swagger) once the
backend is running — use this file for the *data shapes*, use `/docs` for
the *live request/response* to try calls.

**Live database**: hosted on Supabase, org "DealFlow", project "Deal.it"
(`rvtcsaqffcrtycbjkhcc`). All 20 tables below are created and seeded there.
Connect via the **session pooler** (the direct `db.<ref>.supabase.co` host is
IPv6-only and will fail to resolve on IPv4-only networks):
```
postgresql://postgres.rvtcsaqffcrtycbjkhcc:<password>@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres
```
Ask Person 1 for the password, or get it from Supabase → Project Settings →
Database → Connect. Put it in `backend/.env` as `DATABASE_URL` (with
`+psycopg2` after `postgresql`) — that file is gitignored, never commit it.

**Auth (added 2026-09-05, enforced fleet-wide same day)**: `POST /auth/login`
(internal) and `POST /portal/login` (customer) both return a JWT —
`Authorization: Bearer <token>`. All `/portal/*` routes except `/portal/login`
and `/portal/magic-link` require a customer-type token. **Every other
endpoint in this doc now requires an internal-type token** — log in as one of
the seeded users below first, then send `Authorization: Bearer <token>` on
every call. A missing/invalid token gets `401`; a customer token on an
internal route (or vice versa) gets `403`.

**CORS**: enabled for all origins by default (`CORSMiddleware`), so a
browser-based frontend on a different port/host can call this API directly.
Set the `CORS_ORIGINS` env var (comma-separated) to restrict it for a real
deployment.

**Frontend (added 2026-09-05)**: `frontend/` is now fully wired to this API
via `frontend/src/api/client.js` — real login, real reads, real writes, no
mock data. `GET /portal/me`, `GET /portal/quotations` (list), and
`GET /portal/negotiations` were added specifically to back the portal's
Profile/My-Quotations/Messages screens. `GET /subscriptions` gained
`?quotation_id=`/`?status=` filters for the billing detail screen. The
portal endpoints also gained an ownership check in this pass: a customer
token can now only read or act on quotations whose `customer_name` matches
its own `Customer.name` — previously any valid customer login could read or
negotiate on any quotation by guessing its id.

**Seeded test credentials** (same password for every seeded user):
```
Internal:  j.rao@dealflow360.example / password123   (sales_rep)
           m.shah@dealflow360.example / password123  (sales_manager)
           k.iyer@dealflow360.example / password123  (finance)
           admin@dealflow360.example / password123   (admin)
Portal:    procurement@acme.example / password123
```

---

## 1. `quotations`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| customer_name | text | |
| customer_tier | text | `"Bronze"` \| `"Silver"` \| `"Gold"` — must match a `discount_tiers.name` row to get auto-filled category limits |
| status | text | one of: `draft`, `pending_approval`, `approved`, `rejected`, `confirmed`, `fulfillment`, `invoiced`, `paid`, `cancelled` (not DB-enforced, convention only) |
| created_at | timestamptz | server-set on insert |
| sales_rep_id | integer, FK -> users.id, nullable | **added 2026-09-05.** Drives the discount-anomaly screen (14) and feeds `rep_avg_discount_pct`/`seniority` into `score_risk()`. Nullable — old rows can stay empty. |
| expected_delivery_date | date, nullable | **added 2026-09-05.** Backs the `GET /deal-health` delivery-slippage indicator — a quotation shows as slipping once this date is past and `actual_delivery_date` is still null. |
| actual_delivery_date | date, nullable | **added 2026-09-05.** Set once fulfillment actually delivers; nothing writes it automatically yet (no delivery-confirmation endpoint exists). |

Relationships: has many `quotation_lines`, `approvals`, `fulfillment_splits`, `invoices`, `negotiation_requests`.

`GET /quotations`, `GET /quotations/{id}`, and `GET /portal/quotations/{id}` all attach a transient **`total_margin`** on the quotation (sum of line margins, computed from `products.cost` — null if any line's product has no cost on record).

## 2. `quotation_lines`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| quotation_id | integer, FK -> quotations.id | |
| product_id | text | free-text product code, e.g. `"LAPTOP-PRO-14"` — matched by convention (not a DB FK) to `products.product_code` |
| category | text | `"Hardware"` \| `"Services"` \| `"Subscription"` |
| qty | integer | |
| unit_price | numeric(12,2) | |
| discount_pct | numeric(5,2) | default 0 |
| category_limit_pct | numeric(5,2) | **snapshotted** at line-creation time. If the client omits it on `POST /quotations` or `PATCH /quotations/{id}/lines`, the backend auto-fills it from `discount_tiers.category_limits[category]` for the quotation's `customer_tier`. Send it explicitly only to override. |

`GET /quotations`, `GET /quotations/{id}`, and the create/update endpoints all attach a **transient `product_name`** field per line (joined from `products.product_code`, not a DB column on this table) — cosmetic, so screens show "Laptop Pro 14" instead of `LAPTOP-PRO-14`.

Those same endpoints also attach a transient **`margin`** per line (**added 2026-09-05**, PDF B3's "live margin indicator") — `(unit_price * (1 - discount_pct/100) - product.cost) * qty`, or `null` if the line's product has no `cost` on record.

## 3. `discount_tiers` (new — added 2026-09-05)

Backend config table (PDF section A3 / wireframe screen 18, "Discount tiers
and approval chains"). One row per tier holds everything that screen
configures.

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| name | text, unique | `"Bronze"` \| `"Silver"` \| `"Gold"` |
| max_discount_pct | numeric(5,2) | overall tier ceiling |
| category_limits | jsonb | `{"Hardware": 15, "Services": 10, "Subscription": 10}` — per-category ceiling for this tier |
| approval_chain | jsonb | `{"LOW": "none", "MEDIUM": "sales_manager", "HIGH": "sales_manager_then_finance"}` — maps a quotation's blended risk to the required approval stage |

Frontend use: the backend admin config screen (16-18 range) reads/writes
this via `GET/POST/PATCH /discount-tiers`. The quotation builder screen (B3)
does **not** need to call this directly — just omit `category_limit_pct` on
line submission and the backend resolves it.

## 4. `approvals`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| quotation_id | integer, FK -> quotations.id | |
| blended_risk | text | `"LOW"` \| `"MEDIUM"` \| `"HIGH"` (from `engines.score_risk()`) |
| stage | text | `"sales_manager"` \| `"finance"` \| `"confirmed"` \| `"rejected"` \| `"returned"` |
| assigned_to | text, nullable | reviewer name |
| history | jsonb | list of `{user, action, note, at}` entries. `POST /quotations/{id}/submit` (added 2026-09-05) seeds this with one `{"action": "flagged", "user": "system", "reason": ..., "at": ...}` entry — `reason` is `score_risk()`'s plain-language explanation. `POST /approvals/{id}/decision` appends further entries with `action` `"approve"` \| `"reject"` \| `"return"`. |
| flagged_lines | jsonb | **added 2026-09-05.** `score_risk()`'s per-line breakdown at submit/confirm time — `[{line, discount_given_pct, limit_allowed_pct, over_by_pct, line_id, product_id, category, line_value}]`. Backs wireframe screen 6's "Why This Quote Was Flagged" table directly; empty list on a LOW-risk approval with nothing flagged. |

A quotation can have more than one `Approval` row over its lifetime (e.g. if
returned then resubmitted); always take the most recently created one for
"current" status unless the UI needs full history.

**Routing note**: every approval now starts at `stage = "sales_manager"`,
whether `blended_risk` is MEDIUM or HIGH. A MEDIUM approve goes straight to
`"confirmed"`. A HIGH approve moves it to `stage = "finance"` instead, and it
takes a *second* `POST /approvals/{id}/decision` (as finance) to reach
`"confirmed"` — a real two-step chain, matching `discount_tiers
.approval_chain.HIGH = "sales_manager_then_finance"`. (Fixed 2026-09-05 —
earlier, HIGH was routed straight to a `"finance"`-only stage that a single
approval fully cleared, skipping the manager step entirely.)

`GET /approvals` (added 2026-09-05) lists all approvals, newest first;
`?pending_only=true` filters to `stage` in `sales_manager`/`finance` (screen
5's badge counts and filter). `GET /approvals/{id}` (added 2026-09-05) fetches
one, for screen 6. Every decision via `POST /approvals/{id}/decision` also now
writes an `audit_logs` row (see section 17) alongside the `history` entry.

## 5. `warehouses`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| name | text | e.g. `"Main Warehouse"`, `"East Depot"` |
| stock | jsonb | list of `{product_id, qty}` |
| shipping_cost_per_unit | numeric(10,2) | **added 2026-09-05**, default 0. Passed straight through to `engines.split_warehouse()` so it can compute real per-line shipping cost. |
| shipment_fixed_cost | numeric(10,2) | **added 2026-09-05**, default 0. Flat per-shipment cost from this warehouse, also passed to the engine. |
| replenishment_rules | jsonb | **added 2026-09-05**, default `{}`. Free-form (e.g. `{"reorder_point": 10, "reorder_qty": 40}`) — PDF A4's "replenishment rules per warehouse". Nothing currently *acts* on these values automatically (no reorder job); they're config data for the admin warehouse-setup screen to read/write. |

## 6. `fulfillment_splits`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| quotation_id | integer, FK -> quotations.id | one row per quotation (upserted on each `GET /fulfillment/{quotation_id}` call) |
| splits | jsonb | list of `{warehouse_id, qty, cost}` — one entry per (line, warehouse) the engine assigned real stock from. **Rows the engine marks `is_backorder: true` are filtered out before persisting** (added 2026-09-05) — they never appear here. |

`GET /fulfillment/{quotation_id}`'s response also includes a **transient `backorders`** array (not persisted to this table) — one entry per line the engine couldn't fully source, used to drive the "Consolidate Remaining Backorder" prompt (wireframe B6).

## 7. `subscriptions`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| customer_name | text | |
| plan | text | e.g. `"Care Plan 2yr"` |
| cycle | text | `"Monthly"` \| `"Quarterly"` \| `"Yearly"` |
| next_bill_date | date, nullable | |
| status | text | default `"active"` |
| amount | numeric(12,2), nullable | **added 2026-09-05.** The current recurring charge. Set it on `POST /subscriptions` (or via `PATCH .../{id}`) to unlock real proration math below — leave it null and proration/refunds simply won't auto-compute. |
| qty | integer, nullable | **added 2026-09-05.** Recurring seat/unit count, informational — not itself used in the proration formula (that's driven by `amount`). |
| quotation_id | integer, FK -> quotations.id, nullable | **added 2026-09-05.** Links a subscription back to the quotation it was created from, when there is one. |

**Real proration (added 2026-09-05)**: `PATCH /subscriptions/{id}` now
accepts `amount`/`qty` and returns `{subscription, proration_amount,
credit_note}` instead of a bare `Subscription` — a **response shape change**
from the first pass. `proration_amount = (new_amount - old_amount) *
(days_remaining_in_cycle / cycle_length_days)` (cycle lengths: Monthly=30,
Quarterly=90, Yearly=365 days; `days_remaining` comes from `next_bill_date`,
or the full cycle if that's null). A negative result (downgrade) auto-creates
a `credit_notes` row, returned inline as `credit_note`. A positive result
(upgrade) is reported but **not** auto-invoiced — raise that charge manually
via `POST /invoices` if needed.

`POST /subscriptions/{id}/cancel`'s `refund_amount` is now optional: when
omitted and the subscription has both `amount` and `next_bill_date` set, the
refund is auto-computed with the same formula above; passing `refund_amount`
explicitly still overrides it.

## 8. `invoices`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| quotation_id | integer, FK -> quotations.id | |
| amount | numeric(12,2) | |
| status | text | `"unpaid"` \| `"paid"` (convention, not DB-enforced) |
| due_date | date, nullable | |

**Resolved 2026-09-05**: an `Invoice` is now auto-created (amount = sum of
`unit_price * qty * (1 - discount_pct/100)` across lines) the moment a
quotation reaches `confirmed`/`approved` — either immediately in
`POST /quotations/{id}/submit` (no approval needed) or when
`POST /approvals/{id}/decision` clears the full chain. `POST /invoices` also
exists for manual/admin creation. `POST /invoices/{id}/pay` (see `payments`,
section 18 below) closes it out — this is what makes Quick Test Flow step 8
work end to end.

---

## Second pass (2026-09-05): tables that were missing entirely

The first pass only covered the quotation-to-cash core. Going back through
the PDF section by section surfaced 12 more tables with **no backing schema
at all** — most notably Users/Roles (PDF section 3), which every role in the
platform depends on. A third pass (2026-09-05) then closed every remaining
API gap — auth, the customer portal negotiation flow, invoicing/payments,
upsell, warehouse/product/subscription-plan CRUD, and reporting. See
`API_CONTRACT.md`'s Endpoints section for the full current list (41 endpoints).
`price_lists`, `product_variants`, `credit_notes`, and `audit_logs` remain
schema-only (no dedicated CRUD) — they're written to as side effects of
other endpoints (product create/update, subscription cancel, quotation edits)
rather than managed directly.

## 9. `users`

Internal users (PDF section 3: Sales Rep, Sales Manager/Approver,
Finance/Operations User, Admin — Customer is a separate portal role, see
`customer_users` below).

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| name | text | |
| email | text, unique | |
| password_hash | text | real bcrypt hash (added 2026-09-05) — set via `POST /auth/signup` or seeded with `api.auth_utils.hash_password()` |
| role | text | `"sales_rep"` \| `"sales_manager"` \| `"finance"` \| `"admin"` |
| created_at | timestamptz | |
| seniority | smallint, nullable | **added 2026-09-05.** `0` junior, `1` mid, `2` principal. Only meaningful for `role = "sales_rep"` — a stronger risk-model signal than `role` alone, since a rep's seniority varies independent of role. Feeds `score_risk()`. |
| status | text, `NOT NULL DEFAULT 'approved'` | **added 2026-09-05** (feature-completion pass), applied via an additive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` run at app startup so it's safe against both local Postgres and the already-populated Supabase DB. `"pending"` \| `"approved"` \| `"rejected"`. `POST /auth/signup` always creates `"pending"` rows; `POST /auth/login` rejects non-`"approved"` accounts with 403. An Admin flips this via `POST /admin/users/{id}/approve`\|`reject`. The column default keeps every pre-existing (seeded) user `"approved"` without needing a backfill. |

## 10. `customers`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| name | text, unique | e.g. `"Acme Corp"` |
| default_tier | text | Bronze/Silver/Gold |
| created_at | timestamptz | |
| status | text, `NOT NULL DEFAULT 'approved'` | **added 2026-09-06.** `"pending"` \| `"approved"` \| `"rejected"`. Mirrors `users.status`'s pattern exactly. A company created by an internal user (`POST /customers`) is auto-`"approved"`; one created via self-service `POST /portal/signup` starts `"pending"` and stays invisible to `GET /customers` (the quotation builder's picker defaults to `?status=approved`) and unable to log in until an Admin approves it via `POST /admin/customers/{id}/approve`. Applied via the same additive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` pattern at app startup. |

**Not FK-linked from `quotations`** — `quotations.customer_name`/`customer_tier` stay free-text/snapshot fields (per the existing contract, to avoid an ALTER on the deployed table). Join by matching `quotations.customer_name == customers.name` when you need one; a real FK is a follow-up contract change.

## 11. `customer_users`

Portal login for a customer contact (PDF A1: "magic link, or email and password"). This is what the separate, restricted customer negotiation screen (B8) authenticates against.

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| customer_id | integer, FK -> customers.id | |
| email | text, unique | |
| password_hash | text, nullable | null when `auth_method` is `magic_link` |
| auth_method | text | `"password"` \| `"magic_link"` |
| created_at | timestamptz | |

## 12. `products`

PDF A2 (Product & Price List Management — General Info).

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| product_code | text, unique | matches the free-text `product_id` strings used on `quotation_lines` and inside `warehouses.stock[]`, e.g. `"LAPTOP-PRO-14"` |
| name | text | |
| category | text | Hardware / Services / Subscription |
| price | numeric(12,2) | |
| cost | numeric(12,2), nullable | **added 2026-09-05.** Basis for margin calc (`price - cost`) — stored as cost rather than a precomputed margin so it stays correct when a `price_lists` entry overrides the effective price. |
| is_promoted | boolean | **added 2026-09-05**, default false. Ranks the product higher in upsell suggestions (B5). |
| promo_tag | text, nullable | **added 2026-09-05.** Display label for a promoted product, e.g. `"Bundle Deal"` — shown on wireframe screen 4's upsell panel. |
| unit | text | default `"each"` |
| tax_pct | numeric(5,2) | |
| description | text, nullable | |
| is_subscription | boolean | |
| recurring_cycle | text, nullable | Monthly/Quarterly/Yearly, if `is_subscription` |
| quantity_on_hand | integer, nullable | |

## 13. `product_variants`

PDF A2 (Variants: Attribute, Values, Extra prices).

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| product_id | integer, FK -> products.id | |
| attribute | text | e.g. `"RAM"` |
| value | text | e.g. `"16GB"` |
| extra_price | numeric(12,2) | |

## 14. `price_lists`

PDF A2 (Price Lists: customer tier based pricing, currency specific rules).

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| product_id | integer, FK -> products.id | |
| customer_tier | text | |
| currency | text | default `"USD"` |
| price_rule | jsonb | e.g. `{"type": "fixed", "price": 1150.00}` or `{"type": "markup_pct", "value": 10}` — shape is a convention, not enforced |

## 15. `subscription_plans`

PDF A5 — the reusable **plan definition** (proration + cancellation rules), distinct from `subscriptions` (a customer's live instance of a plan).

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| name | text | e.g. `"Care Plan 2yr"` |
| cycle | text | Monthly/Quarterly/Yearly |
| proration_rule | jsonb | mid-cycle qty/plan change rules |
| cancellation_rule | jsonb | refund/credit-note rules |

## 16. `upsell_rules`

PDF A6 (optional) — product pairings for the Upsell/Cross-Sell Panel (B5).

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| source_product_id | integer, FK -> products.id | the cart item |
| suggested_product_id | integer, FK -> products.id | the suggestion |
| is_promoted | boolean | ranks higher in suggestions |
| min_margin_pct | numeric(5,2) | only surface if margin clears this |
| suggestion_type | text, default `'cross_sell'` | **added 2026-09-06.** `"upsell"` (a richer plan/tier for the same purchase, e.g. Extended Warranty → Premium Support Plan) vs `"cross_sell"` (a separate, complementary product, e.g. Laptop → Docking Station). Admin-set per pairing on creation, never inferred at query time — the ranking engine only passes it through. |

## 17. `audit_logs`

PDF A3 note: *"All approvals, rejections, and edits must be logged with user, timestamp, and reason."* `approvals.history` already covers approval decisions specifically; this table covers everything else (line edits, config changes) across any entity.

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| entity_type | text | e.g. `"quotation"`, `"discount_tier"` |
| entity_id | integer | not a DB-enforced FK — points into whichever table `entity_type` names |
| user_id | integer, FK -> users.id, nullable | |
| action | text | e.g. `"create"`, `"edit"`, `"delete"` |
| reason | text, nullable | |
| before | jsonb, nullable | |
| after | jsonb, nullable | |
| created_at | timestamptz | |

## 18. `payments`

Backs Quick Test Flow step 8 ("confirm the order, record a payment, and check that the invoice status updates correctly") — no table existed for this before.

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| invoice_id | integer, FK -> invoices.id | |
| amount | numeric(12,2) | |
| method | text | default `"manual"` |
| paid_at | timestamptz | |

## 19. `credit_notes`

PDF B7: "automatic partial refund or credit note trigger" on subscription cancel/modify.

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| subscription_id | integer, FK -> subscriptions.id, nullable | |
| invoice_id | integer, FK -> invoices.id, nullable | |
| amount | numeric(12,2) | |
| reason | text, nullable | |
| created_at | timestamptz | |

## 20. `negotiation_requests`

PDF B8 (Customer Portal Negotiation Screen): line-level comment/change-request tool + counter discount proposal field + Submit Request button.

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| quotation_id | integer, FK -> quotations.id | |
| quotation_line_id | integer, FK -> quotation_lines.id, nullable | null = quotation-level comment |
| customer_user_id | integer, FK -> customer_users.id, nullable | |
| message | text, nullable | |
| counter_discount_pct | numeric(5,2), nullable | |
| status | text | `"pending"` \| `"resolved"` |
| created_at | timestamptz | |

---

## Entity-relationship summary

```
quotations 1---* quotation_lines
quotations 1---* approvals
quotations 1---1 fulfillment_splits    (one row, upserted)
quotations 1---* invoices
quotations 1---* negotiation_requests
quotation_lines 1---* negotiation_requests  (optional line-level link)
invoices 1---* payments
invoices 1---* credit_notes  (optional)
subscriptions 1---* credit_notes  (optional)

discount_tiers (standalone config; joined to quotations by matching
                quotations.customer_tier == discount_tiers.name)
warehouses (standalone; referenced by product_id inside its own stock[])
quotations 1---* subscriptions  (optional, via subscriptions.quotation_id, added 2026-09-05)

customers 1---* customer_users
customer_users 1---* negotiation_requests

products 1---* product_variants
products 1---* price_lists
products 1---* upsell_rules (as source_product_id)
products 1---* upsell_rules (as suggested_product_id)
quotation_lines.product_id (free text) <--matches--> products.product_code

users 1---* audit_logs (as user_id, nullable)
```

## Conventions the frontend should rely on

- All money fields are numeric(12,2) — treat as decimal strings/floats, don't assume integer cents.
- All list-of-object / JSON columns (`history`, `stock`, `splits`, `category_limits`, `approval_chain`, `price_rule`, `proration_rule`, `cancellation_rule`, `before`, `after`) are plain JSON — no separate tables, no pagination inside them.
- `status`, `stage`, `role`, `auth_method`, `method` string values above are conventions enforced in application code, not DB constraints — don't assume the DB will reject an unexpected string.
- `id` fields are all integers. The wireframes show human-readable codes like `Q-1042` — the API does not use those; the frontend should generate/display its own display code (e.g. `Q-` + zero-padded id) if that formatting is wanted.
- **Auth exists now** (added 2026-09-05) — see the credentials block near the top of this file. `password_hash` values are real bcrypt hashes for every seeded row.
- `product_id` on `quotation_lines` and inside `warehouses.stock[]` is a free-text string, matched by convention to `products.product_code` — not a DB-enforced FK.
- **Every internal endpoint requires auth now** (enforced 2026-09-05) — send `Authorization: Bearer <token>` from `POST /auth/login` on every call except `/auth/*` and `/portal/*`. No token or the wrong token type returns `401`/`403`, not a silent empty result.
- **`GET /dashboard/summary`** (added 2026-09-05, no dedicated table — computed live from `approvals`, `quotations`, and the deal-health logic) backs wireframe screen 2: `{pending_approvals, open_quotations, at_risk_deals, recent_activity[]}`. `recent_activity` merges `audit_logs`, `approvals.history`, and `negotiation_requests` into one newest-first feed — there's no single "activity" table.
- `quotations.status` gained a `"negotiation"` value (added 2026-09-05) — set when a customer submits a negotiation request via `POST /portal/quotations/{id}/negotiate`, cleared back to `pending_approval`/`confirmed` on `POST /portal/quotations/{id}/confirm`.
