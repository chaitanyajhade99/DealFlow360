# DealFlow360 frontend

React + Vite + React Router + Tailwind CSS. Fully wired to the live backend
(`backend/api`) — no mock data, no local-only write stubs.

## Run

```bash
npm install
cp .env.example .env   # points VITE_API_BASE at the backend (default http://127.0.0.1:8000)
npm run dev
```

Start the backend first (`cd ../backend && uvicorn api.main:app --reload`) and
seed it (`python -m seed.seed`) so there's real data to log in against.

## Build

```bash
npm run build
```

## Architecture

- `src/api/client.js` — the only place that talks to the backend. Every
  function makes a real `fetch()` call and stores/attaches JWTs from
  `POST /auth/login` (internal) and `POST /portal/login` (customer) —
  separate sessions in `localStorage` so both can be open at once.
- `src/context/RoleContext.jsx` — real auth state (`internalUser`,
  `customerProfile`, `role`, `loginInternal`, `loginPortal`, `logout`),
  backed by the sessions in `client.js`.
- `src/components/InternalRouteGuard.jsx` / `PortalRouteGuard.jsx` — redirect
  to `/` when there's no valid session, instead of rendering with fake data.
- `src/components/ListScreen.jsx` / `DetailScreen.jsx` / `StatusStepper.jsx` —
  reusable shells.

## Routes

Internal (requires an internal login):
- `/app`, `/app/quotations`, `/app/quotations/new`, `/app/quotations/:id`
- `/app/approvals`, `/app/approvals/:id`
- `/app/fulfillment`, `/app/fulfillment/:id`
- `/app/subscriptions`, `/app/billing/:id`
- `/app/invoices`, `/app/invoices/:id`
- `/app/deal-health`, `/app/reports`
- Admin-only: `/app/admin/products`, `/app/admin/discount-config`,
  `/app/admin/warehouses`, `/app/admin/subscription-plans`,
  `/app/admin/users`, `/app/admin/customers`, `/app/admin/reporting`

Customer portal (requires a portal login, separate session):
- `/portal`, `/portal/:quotationId`, `/portal/billing`, `/portal/messages`, `/portal/profile`

Public:
- `/` (login), `/signup` (internal team sign-up + customer portal sign-up)

## What's real

Every screen reads and writes through `client.js` to the actual FastAPI
backend and Postgres database — quotation creation/editing/submission,
the two-step Sales-Manager-then-Finance approval chain (with an editable
decision note and an "Edit Quotation" shortcut after a Return), warehouse
fulfillment splits, subscription proration and cancellation, invoice
payment (manual or real Razorpay Checkout, test mode), quotation PDF
export, the customer portal negotiate → auto-reenter-approval loop,
self-service sign-up for both internal staff (Admin-approved) and customer
accounts, admin user approvals, and full admin CRUD for products, discount
tiers, warehouses, and subscription plans.

## Known, honest limitations

1. **Fulfillment "Manual Override"** stays a local preview. The backend
   computes the real suggested split from live stock/cost (`GET
   /fulfillment/{id}`), but there is no contract-specified write endpoint to
   persist a manual override — the PDF never calls for one.
2. **XLS export** on the Reports screen is not implemented (PDF export
   exists for quotations, via `GET /quotations/{id}/pdf`). Every number on
   the Reports screen is still live from the backend.
3. Internal endpoints don't have per-role UI restrictions beyond the Admin
   area — e.g. a Sales Rep can technically open the Approvals screen. The
   backend only distinguishes internal-vs-customer tokens, not per-role
   scopes, so the frontend doesn't invent restrictions the API doesn't
   enforce.
4. **Razorpay** runs in TEST mode against the key pair in `backend/.env` —
   use Razorpay's published test card/UPI credentials at checkout, never a
   real card.
