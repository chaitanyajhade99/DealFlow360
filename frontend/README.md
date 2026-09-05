# DealFlow360 frontend

Frontend-only React + Vite + React Router + Tailwind CSS implementation for the 24-hour hackathon flow.

## Run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Architecture

- `src/components/ListScreen.jsx` — reusable list shell.
- `src/components/DetailScreen.jsx` — reusable detail shell with optional side panel.
- `src/components/StatusStepper.jsx` — reusable status tracker.
- `src/api/client.js` — thin API boundary. Flip an individual `USE_MOCKS` key from `true` to `false` to call the real endpoint without changing screens.
- `src/api/mockData.js` — mock objects shaped to the supplied Postgres schema.

## Routes

Internal:
- `/`
- `/app`
- `/app/quotations`
- `/app/quotations/1042`
- `/app/approvals`
- `/app/approvals/501`
- `/app/fulfillment`
- `/app/fulfillment/1037`
- `/app/subscriptions`
- `/app/billing`
- `/app/invoices`
- `/app/invoices/9001`
- `/app/deal-health`
- `/app/reports`

Separate customer portal:
- `/portal`
- `/portal/messages`
- `/portal/profile`

## Contract flags / known gaps

1. **Auth**: no login/signup endpoints exist yet. Login is deliberately mock-only.
2. **Invoices**: the supplied schema says `GET /invoices` is read-only and no endpoint currently creates Invoice rows. "Record Payment" is therefore a UI placeholder.
3. **Fulfillment writes**: the supplied schema describes `fulfillment_splits` but does not specify a write endpoint in the brief, so Manual Override is local-only until that endpoint exists.
4. **Subscriptions**: `subscriptions` has no `quotation_id` FK, so the UI does not invent a quotation relationship.
5. **Deal Health delivery slippage**: no promised-delivery/SLA field exists in the supplied schema, so the stretch dashboard treats fulfillment state as the available delivery-risk signal.
6. **Quotation line editing**: the discount editor demonstrates the required live per-line check. It calls a local adapter now; replace that function with the real PATCH when the endpoint is available.

## Wireframe treatment

The UI follows the supplied wireframe's compact blue DealFlow360 navigation, white card/table surfaces, yellow callout banners, small status chips, and separate portal shell. Admin/reporting and product/config screens are intentionally not implemented as requested.
