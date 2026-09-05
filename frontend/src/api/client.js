// Real API client for the DealFlow360 backend. No mocks -- every function
// here makes a real HTTP call to FastAPI and returns real data from Postgres.
//
// Auth: internal endpoints need an "internal" JWT (POST /auth/login), portal
// endpoints need a "customer" JWT (POST /portal/login). Both are stored in
// localStorage under separate keys so a browser tab can hold both sessions
// at once (e.g. testing the ops console and the customer portal side by side).

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const STORAGE_KEYS = {
  internal: "dealflow360.internal.session",
  customer: "dealflow360.customer.session",
};

function readSession(kind) {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS[kind]);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeSession(kind, session) {
  try {
    if (session) localStorage.setItem(STORAGE_KEYS[kind], JSON.stringify(session));
    else localStorage.removeItem(STORAGE_KEYS[kind]);
  } catch {
    /* storage unavailable -- session just won't persist across reloads */
  }
}

export function getInternalSession() {
  return readSession("internal");
}
export function getCustomerSession() {
  return readSession("customer");
}
export function setInternalSession(session) {
  writeSession("internal", session);
}
export function setCustomerSession(session) {
  writeSession("customer", session);
}
export function clearInternalSession() {
  writeSession("internal", null);
}
export function clearCustomerSession() {
  writeSession("customer", null);
}

class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : detail?.detail || `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, { method = "GET", body, auth = "internal", signal } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const session = auth === "customer" ? getCustomerSession() : getInternalSession();
    if (session?.token) headers.Authorization = `Bearer ${session.token}`;
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (response.status === 401 || response.status === 403) {
    // Session is dead -- drop it so route guards bounce back to login
    // instead of the app quietly showing empty screens forever.
    if (auth === "customer") clearCustomerSession();
    else if (auth === "internal") clearInternalSession();
  }

  let payload = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) throw new ApiError(response.status, payload);
  return payload;
}

const get = (path, opts) => request(path, { ...opts, method: "GET" });
const post = (path, body, opts) => request(path, { ...opts, method: "POST", body });
const patch = (path, body, opts) => request(path, { ...opts, method: "PATCH", body });

function qs(params = {}) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (!entries.length) return "";
  return "?" + new URLSearchParams(entries).toString();
}

// ---- Auth (internal) ----
export async function loginInternal(email, password) {
  const data = await post("/auth/login", { email, password }, { auth: null });
  setInternalSession({ token: data.access_token, user: data.user });
  return data;
}
export async function signupInternal(payload) {
  return post("/auth/signup", payload, { auth: null });
}
export function logoutInternal() {
  clearInternalSession();
}

// ---- Auth (customer portal) ----
export async function loginPortal(email, password) {
  const data = await post("/portal/login", { email, password }, { auth: null });
  // Store the token first so the follow-up /portal/me call (which needs
  // Authorization: Bearer <token>) can authenticate itself.
  setCustomerSession({ token: data.access_token, customerId: data.customer_id, customerUserId: data.customer_user_id });
  const profile = await get("/portal/me", { auth: "customer" }).catch(() => null);
  setCustomerSession({ token: data.access_token, customerId: data.customer_id, customerUserId: data.customer_user_id, profile });
  return data;
}
export async function requestPortalMagicLink(email) {
  return post("/portal/magic-link", { email }, { auth: null });
}
export function logoutPortal() {
  clearCustomerSession();
}
export async function getPortalMe() {
  return get("/portal/me", { auth: "customer" });
}
export async function signupPortal({ companyName, email, password }) {
  const data = await post(
    "/portal/signup",
    { company_name: companyName, email, password },
    { auth: null }
  );
  setCustomerSession({ token: data.access_token, customerId: data.customer_id, customerUserId: data.customer_user_id });
  const profile = await get("/portal/me", { auth: "customer" }).catch(() => null);
  setCustomerSession({ token: data.access_token, customerId: data.customer_id, customerUserId: data.customer_user_id, profile });
  return data;
}

// ---- Admin: user approval ----
export async function getAdminUsers(status) {
  return get(`/admin/users${qs({ status })}`);
}
export async function approveUser(id) {
  return post(`/admin/users/${id}/approve`, {});
}
export async function rejectUser(id) {
  return post(`/admin/users/${id}/reject`, {});
}

// ---- Dashboard ----
export async function getDashboardSummary(activityLimit = 10) {
  return get(`/dashboard/summary${qs({ activity_limit: activityLimit })}`);
}

// ---- Quotations ----
export async function getQuotations() {
  return get("/quotations");
}
export async function getQuotationDetail(id) {
  const quotation = await get(`/quotations/${id}`);
  return { quotation, lines: quotation.lines || [] };
}
export async function createQuotation(payload) {
  return post("/quotations", payload);
}
export async function updateQuotationLines(id, payload) {
  return patch(`/quotations/${id}/lines`, payload);
}
export async function submitQuotation(id) {
  return post(`/quotations/${id}/submit`, {});
}
export async function getUpsellSuggestions(quotationId) {
  return get(`/quotations/${quotationId}/upsell-suggestions`);
}
export async function downloadQuotationPdf(id) {
  const session = getInternalSession();
  const response = await fetch(`${API_BASE}/quotations/${id}/pdf`, {
    headers: session?.token ? { Authorization: `Bearer ${session.token}` } : {},
  });
  if (!response.ok) throw new ApiError(response.status, "Could not generate PDF");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `quotation-Q-${String(id).padStart(4, "0")}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ---- Approvals ----
export async function getApprovals(pendingOnly = false) {
  return get(`/approvals${qs({ pending_only: pendingOnly || undefined })}`);
}
export async function getApprovalDetail(id) {
  const approval = await get(`/approvals/${id}`);
  const quotation = await get(`/quotations/${approval.quotation_id}`);
  return { approval, quotation, lines: quotation.lines || [] };
}
export async function decideApproval(approvalId, action, note = "", user = "Current User") {
  return post(`/approvals/${approvalId}/decision`, { action, note, user });
}

// ---- Fulfillment ----
export async function getFulfillmentDetail(quotationId) {
  const [quotation, fulfillment, warehouses] = await Promise.all([
    get(`/quotations/${quotationId}`),
    get(`/fulfillment/${quotationId}`),
    get("/warehouses"),
  ]);
  return { quotation, lines: quotation.lines || [], fulfillment, warehouses };
}

// ---- Warehouses ----
export async function getWarehouses() {
  return get("/warehouses");
}
export async function createWarehouse(payload) {
  return post("/warehouses", payload);
}
export async function updateWarehouse(id, payload) {
  return patch(`/warehouses/${id}`, payload);
}

// ---- Subscriptions ----
export async function getSubscriptions(params = {}) {
  return get(`/subscriptions${qs(params)}`);
}
export async function getSubscription(id) {
  return get(`/subscriptions/${id}`);
}
export async function createSubscription(payload) {
  return post("/subscriptions", payload);
}
export async function updateSubscription(id, payload) {
  return patch(`/subscriptions/${id}`, payload);
}
export async function cancelSubscription(id, payload = {}) {
  return post(`/subscriptions/${id}/cancel`, payload);
}
export async function getSubscriptionCreditNotes(id) {
  return get(`/subscriptions/${id}/credit-notes`);
}
export async function getSubscriptionPlans() {
  return get("/subscription-plans");
}
export async function createSubscriptionPlan(payload) {
  return post("/subscription-plans", payload);
}

// ---- Invoices / Payments ----
export async function getInvoices() {
  return get("/invoices");
}
export async function getInvoiceDetail(id) {
  const invoice = await get(`/invoices/${id}`);
  const quotation = await get(`/quotations/${invoice.quotation_id}`);
  return { invoice, quotation, lines: quotation.lines || [] };
}
export async function createInvoice(payload) {
  return post("/invoices", payload);
}
export async function payInvoice(id, payload) {
  return post(`/invoices/${id}/pay`, payload);
}
export async function createRazorpayOrder(id) {
  return post(`/invoices/${id}/razorpay-order`, {});
}
export async function verifyRazorpayPayment(id, payload) {
  return post(`/invoices/${id}/razorpay-verify`, payload);
}

// ---- Deal health ----
export async function getDealHealth() {
  return get("/deal-health");
}
export async function nudgeQuotation(quotationId, payload = {}) {
  return post(`/deal-health/${quotationId}/nudge`, payload);
}
export async function escalateQuotation(quotationId, payload = {}) {
  return post(`/deal-health/${quotationId}/escalate`, payload);
}

// ---- Discount tiers ----
export async function getDiscountTiers() {
  return get("/discount-tiers");
}
export async function createDiscountTier(payload) {
  return post("/discount-tiers", payload);
}
export async function updateDiscountTier(id, payload) {
  return patch(`/discount-tiers/${id}`, payload);
}

// ---- Products ----
export async function getProducts() {
  return get("/products");
}
export async function getProduct(id) {
  return get(`/products/${id}`);
}
export async function createProduct(payload) {
  return post("/products", payload);
}
export async function updateProduct(id, payload) {
  return patch(`/products/${id}`, payload);
}

// ---- Reports ----
export async function getReportSummary(params = {}) {
  return get(`/reports/summary${qs(params)}`);
}

// ---- Customer portal ----
export async function getPortalQuotations() {
  return get("/portal/quotations", { auth: "customer" });
}
export async function getPortalQuotationDetail(id) {
  const quotation = await get(`/portal/quotations/${id}`, { auth: "customer" });
  return { quotation, lines: quotation.lines || [] };
}
export async function submitNegotiationRequest(quotationId, payload) {
  return post(`/portal/quotations/${quotationId}/negotiate`, payload, { auth: "customer" });
}
export async function confirmPortalQuotation(quotationId) {
  return post(`/portal/quotations/${quotationId}/confirm`, {}, { auth: "customer" });
}
export async function getPortalNegotiations() {
  return get("/portal/negotiations", { auth: "customer" });
}

export { ApiError };
