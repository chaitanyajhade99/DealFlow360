# DealFlow360

**An end-to-end B2B Sales Operations & Governance Platform** — from quote
creation through multi-stage discount approval, warehouse fulfillment,
subscription billing, real payment collection, and customer self-service
negotiation. Built as a full-stack hackathon project against a formal PDF
problem statement, now wired together end-to-end with **no mock data
anywhere** — every screen reads and writes a live FastAPI + PostgreSQL
backend.

> Full technical specs live in [`API_CONTRACT.md`](API_CONTRACT.md) (every
> endpoint, with change history) and [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md)
> (every table/column, with rationale). This file is the feature-level map of
> the whole product plus how to run it.

---

## 1. What this system does

DealFlow360 models the full lifecycle of a B2B sale:

```
  Sales Rep builds a quote
        │
        ▼
  Risk engine scores the discount (rule + ML hybrid)
        │
   ┌────┴─────┐
   │ LOW risk │──────────────► auto-confirmed, invoice raised
   └────┬─────┘
        │ MEDIUM / HIGH risk
        ▼
  Sales Manager approval ──► (HIGH only) ──► Finance approval ──► Confirmed
        │                                                            │
        │  Return                                                    ▼
        ▼                                                    Invoice + Fulfillment
  Back to draft, Rep edits & resubmits                                │
                                                                       ▼
                                                          Payment (Razorpay / manual)
                                                                       │
                                                                       ▼
                                                        Customer tier recalculated
                                                       (more closed orders → higher tier)
```

In parallel, a **separate customer portal** lets a buyer log in, counter a
discount, and confirm a quote — which automatically re-enters the same
approval pipeline if the final terms breach policy.

---

## 2. Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python), Pydantic v2 schemas |
| Database | PostgreSQL (local or Supabase), SQLAlchemy 2.0 ORM |
| Auth | JWT (PyJWT) + bcrypt password hashing — two independent token types (internal vs. customer) |
| Risk / ML engine | Hybrid: deterministic rules + XGBoost escalation, Apriori association mining (from scratch, no `mlxtend`) |
| PDF generation | reportlab |
| Payments | Razorpay Checkout (test mode) with server-side HMAC-SHA256 signature verification |
| Frontend | React 18 + Vite 6 + React Router 7 + Tailwind CSS 3 + lucide-react + recharts |
| No mocks | Every frontend screen calls a real backend endpoint; no `mockData.js`, no local-only write stubs |

---

## 3. Repository layout

```
DealFlow360/
├── API_CONTRACT.md        ← full endpoint reference, dated change history
├── DATABASE_SCHEMA.md     ← full table/column reference, with rationale
├── DealFlow360.pdf        ← the original problem statement
├── backend/
│   ├── api/               ← FastAPI routers (one file per resource area)
│   ├── models/            ← SQLAlchemy ORM models (one file per table)
│   ├── engines/           ← pure-function risk/fulfillment/anomaly/upsell algorithms
│   │                         (own README.md — no DB access, fully unit-tested)
│   ├── seed/seed.py       ← realistic demo dataset across every lifecycle status
│   ├── demo/run_demo.py   ← narrated, runnable, idempotent 13-step live demo script
│   └── .env               ← DATABASE_URL + Razorpay test keys (gitignored)
└── frontend/
    ├── src/api/client.js  ← the only file that talks to the backend
    ├── src/context/       ← RoleContext (auth), ToastContext (notifications)
    ├── src/components/    ← shared shells: AppShell, PortalShell, route guards, etc.
    └── src/screens/       ← one file per screen, internal + portal + admin
```

---

## 4. Features implemented

### 4.1 Authentication & accounts
- **Internal login** (`POST /auth/login`) — JWT, bcrypt-hashed passwords, role embedded in the token (`sales_rep` / `sales_manager` / `finance` / `admin`).
- **Internal self-service signup** (`POST /auth/signup`, `/signup` page) — requests one of `sales_rep` / `sales_manager` / `finance` (never `admin` — no privilege escalation via signup) and starts `status="pending"`. Login is rejected (403) until an Admin approves.
- **Admin user-approval console** (`/app/admin/users`) — lists pending sign-ups, approve/reject with one click (`GET /admin/users`, `POST /admin/users/{id}/approve|reject`).
- **Customer portal login** (`POST /portal/login`) — a completely separate JWT type, never interchangeable with an internal token (server-side type check on every route).
- **Customer self-service signup** (`POST /portal/signup`, `/signup` page) — auto-approved (no admin gate — blocking it would stop a rep's very first quote to a brand-new account). Links to an existing `Customer` org by company name, or creates one.
- **Magic-link login stub** (`POST /portal/magic-link`) — returns the token directly since no email service is wired up, but the flow is testable end-to-end.
- Two independent sessions can be open in the same browser at once (separate `localStorage` keys) — useful for testing the internal console and the customer portal side by side.

### 4.2 Quotation management
- Full CRUD: create, list, fetch, edit line items (`PATCH .../lines`, logged to `AuditLog` with reason), submit for scoring.
- **Live discount guardrails** in the line editor — a line over its category limit turns red in real time before it's even submitted.
- **Live margin indicator** per line and per quotation, computed from `Product.cost`.
- **Upsell / cross-sell suggestions** on the quote builder, powered by an Apriori-mined co-occurrence engine ranked by expected margin (not just popularity).
- **Quotation PDF export** (`GET /quotations/{id}/pdf`) — a real, generated-on-demand PDF (reportlab) with line items, discounts, and totals. Not cached — always reflects live data.

### 4.3 Risk scoring & multi-stage approval
- **Hybrid risk engine**: a deterministic rule floor (worst single line + blended overage) that a trained XGBoost model may *escalate* above but never lower — so every decision stays explainable (a `reason` string is always produced and stored) while still catching context a pure rule can't (rep seniority, quarter-end timing, deal size).
- **Two real approval stages**: `sales_manager` → (HIGH risk only) → `finance` → `confirmed`. MEDIUM/LOW resolve in a single step. (This was a real bug found and fixed mid-project: HIGH-risk quotes used to skip straight to a finance-only approval.)
- **"Why This Quote Was Flagged" breakdown** — every flagged line's discount vs. its limit, persisted (not recomputed and discarded) so it can be reviewed later.
- **Editable decision notes** — Approve / Return / Reject open a modal for a real audit-trail note instead of a hardcoded string.
- **Return-to-draft with an edit shortcut** — a returned quotation goes back to `draft` and the Approval screen surfaces a direct "Edit Quotation" button once it's resolved that way.
- **Full audit trail** — every approval decision and every line edit is logged with user, timestamp, and reason (`AuditLog`), and merged into the Dashboard's activity feed.

### 4.4 Fulfillment
- **Warehouse split engine** — greedy, deepest-stock-first allocation across warehouses, with backorder detection when no warehouse can fully cover a line.
- Real shipping cost computation (`shipment_fixed_cost + shipping_cost_per_unit * qty`) and per-warehouse `replenishment_rules` (reorder point / reorder quantity) manageable from the admin **Warehouses** screen.

### 4.5 Subscriptions & recurring billing
- Full subscription CRUD, plan configuration (billing cycle, proration rule, cancellation rule) from the admin **Subscription Plans** screen.
- **Real mid-cycle proration math**: `(new_amount - old_amount) * (days_remaining_in_cycle / cycle_length_days)` — a downgrade auto-creates a `CreditNote`; an upgrade is reported but not auto-invoiced (raised manually).
- **Real cancellation refunds**, computed the same way when not explicitly overridden.

### 4.6 Invoicing & payments
- Auto-generated invoices the moment a quotation is fully confirmed (whether that took zero, one, or two approval steps).
- **Real Razorpay Checkout integration** (test mode) — `POST /invoices/{id}/razorpay-order` creates a server-side order (amount can't be tampered with client-side); `POST /invoices/{id}/razorpay-verify` verifies the HMAC-SHA256 signature server-side before ever marking an invoice paid. A forged/incorrect signature is rejected — an invoice cannot be marked paid without a genuinine, verified transaction.
- **Manual/offline reconciliation** kept as a clearly-separated, confirmation-gated Finance action (bank reference required) — not a one-click shortcut, so it can't be confused with or substituted for a real payment.

### 4.7 Customer tiering (earned, not chosen)
- A new customer organization always starts at **Bronze** — tier is never self-selected at signup.
- **Automatic tier recalculation** (`api/tiering.py`) runs every time one of a customer's quotations reaches a closed state: **Bronze → Silver at 3 closed orders, Silver → Gold at 7.** A higher tier unlocks a higher discount ceiling via `DiscountTier.category_limits`, so buying more genuinely earns better terms.

### 4.8 Deal health & governance
- **Stalled deal detection**, **discount anomaly detection** (per-rep z-score — 18% is routine for one rep and alarming for another), and **delivery slippage** (past expected delivery with no actual delivery date).
- One-click **Nudge** / **Escalate** actions from the Deal Health screen, logged to the audit trail and surfaced on the Dashboard.

### 4.9 Customer portal (separate, restricted app)
- Own login, own routes (`/portal/*`), own route guard — structurally isolated from the internal console (a customer JWT is rejected by every internal endpoint and vice versa).
- View your own quotations only — **ownership-enforced server-side** (a real security gap found and fixed: a customer token used to be able to read/negotiate on *any* quotation by guessing its id; now 404s unless `Quotation.customer_name` matches the caller's own account).
- **Negotiate**: counter a line's discount with a message.
- **Confirm Quotation**: applies the latest counter-discount, re-scores it, and — if the final terms breach policy — automatically re-enters the same internal approval pipeline used for reps' own quotes. No separate "customer approval" code path to keep in sync.
- **Messages** — every negotiation request across the account's quotations, and a **Profile** page with real account details.

### 4.10 Admin console
- **Products & Pricing** — full catalogue CRUD, including variants and per-tier price lists.
- **Discount Tiers & Approval Chains** — per-tier, per-category discount ceilings and the risk→stage routing table (PDF A3).
- **Warehouses** — stock levels, shipping costs, replenishment rules.
- **Subscription Plans** — billing cycle, proration, and cancellation rules.
- **User Approvals** — approve/reject pending internal sign-ups (see §4.1).
- **Reporting** — filterable (date range, approval status, category) KPIs and a live per-category revenue breakdown, all derived from real quotation data — no fabricated chart data.

### 4.11 Dashboard
- Real `pending_approvals` / `open_quotations` / `at_risk_deals` counts and a real activity feed — merged from `AuditLog`, `Approval.history`, and `NegotiationRequest`, newest first. Nothing here is client-computed from a stale mock list.

---

## 5. Running it locally

### 5.1 Backend

```bash
cd backend
pip install -r requirements.txt

# backend/.env (gitignored) must set DATABASE_URL, e.g.:
#   DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/dealflow360
#   RAZORPAY_KEY_ID=rzp_test_...
#   RAZORPAY_KEY_SECRET=...

python -m seed.seed          # populates a realistic demo dataset (safe to rerun on a fresh DB)
uvicorn api.main:app --reload
```

- API root: `http://127.0.0.1:8000`
- Interactive docs (Swagger): `http://127.0.0.1:8000/docs`
- Health check: `GET /health`

Schema changes since the tables were first created (e.g. `users.status`) are
applied automatically at startup via additive `ALTER TABLE ... ADD COLUMN IF
NOT EXISTS` statements — safe to run against an already-populated database.

### 5.2 Frontend

```bash
cd frontend
npm install
cp .env.example .env     # VITE_API_BASE, defaults to http://127.0.0.1:8000
npm run dev
```

Open the printed URL (typically `http://localhost:5173`).

### 5.3 Seeded credentials

| Type | Email | Password | Role / Account |
|---|---|---|---|
| Internal | `j.rao@dealflow360.example` | `password123` | Sales Rep |
| Internal | `p.nair@dealflow360.example` | `password123` | Sales Rep (junior) |
| Internal | `m.shah@dealflow360.example` | `password123` | Sales Manager |
| Internal | `k.iyer@dealflow360.example` | `password123` | Finance |
| Internal | `admin@dealflow360.example` | `password123` | Admin |
| Portal | `procurement@acme.example` | `password123` | Acme Corp (Gold) |
| Portal | `ops@globex.example` | `password123` | Globex Manufacturing (Gold) |

Seed data spans every quotation lifecycle status (draft, pending approval,
negotiation, approved, confirmed, rejected), a paid invoice, an active and a
cancelled subscription (with a credit note), and real audit history — the app
looks populated on first login, not empty.

### 5.4 Backend-only demo script

A narrated, idempotent, 13-step script that exercises the backend end-to-end
without any UI — useful for proving the API works in isolation:

```bash
cd backend
python demo/run_demo.py
```

---

## 6. End-to-end flow to click through

1. **Login** as J. Rao (Sales Rep) → Dashboard shows real counts + activity.
2. **Quotations → New Quotation** → add a line discounted above its category limit → **Submit for Approval** → routes to Sales Manager (HIGH risk).
3. **Log out, log in as M. Shah** (Sales Manager) → **Approvals** → open it → see the real flagged-line breakdown → **Approve** with a note → escalates to Finance (or confirms outright for MEDIUM/LOW).
4. **Log in as K. Iyer** (Finance) → approve the same item → quotation confirms, invoice auto-generates.
5. **Invoices** → open the new invoice → **Pay with Razorpay** (test card) → invoice flips to paid only after signature verification succeeds.
6. **Fulfillment** → see the real warehouse split and shipping cost.
7. **Subscriptions** → modify an active subscription's amount → see the real prorated charge/credit; **Cancel** another → see the real refund + credit note.
8. **Deal Health** → **Nudge** / **Escalate** an alert → confirm it appears in Dashboard activity.
9. **Log out, sign up a new customer** at `/signup` (Customer Portal tab, no tier field) → note the account starts Bronze.
10. **Portal**: negotiate a counter-discount on a quote → **Confirm Quotation** → watch it either confirm outright or re-enter the internal approval queue.
11. **Admin** (`admin@dealflow360.example`): approve a pending internal sign-up, edit a discount tier, add a warehouse, add a subscription plan.

---

## 7. Honest, known limitations

1. **Fulfillment "Manual Override"** is a local UI preview only — there's no contract-specified write endpoint to persist a manual override (the PDF never calls for one).
2. **XLS export** on Reports is not implemented (PDF export exists for quotations).
3. Internal endpoints distinguish internal-vs-customer tokens, not per-role scopes beyond the Admin gate — e.g. a Sales Rep can technically open the Approvals screen; the backend doesn't restrict by role beyond `admin`.
4. **Razorpay runs in TEST mode** — use Razorpay's published test card/UPI details at checkout, never a real card.

---

## 8. Further reading

- [`API_CONTRACT.md`](API_CONTRACT.md) — every endpoint, request/response shape, and a dated changelog of every gap-closure pass.
- [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) — every table and column, with the reasoning behind each addition.
- [`backend/engines/README.md`](backend/engines/README.md) — the risk/fulfillment/anomaly/upsell algorithm layer: why the risk model is a hybrid and not pure ML, the Apriori implementation, tunable constants, and 94 unit tests.
- [`frontend/README.md`](frontend/README.md) — frontend architecture, route list, and what's real vs. known limitations.
