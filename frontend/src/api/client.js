import * as mock from "./mockData";

export const USE_MOCKS = {
  quotations: true,
  quotationDetail: true,
  approvals: true,
  approvalDetail: true,
  warehouses: true,
  fulfillment: true,
  subscriptions: true,
  invoices: true,
  invoiceDetail: true,
  negotiationRequests: true,
  discountTiers: true,
};

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json();
}

const clone = (value) => JSON.parse(JSON.stringify(value));

export async function getQuotations() {
  if (USE_MOCKS.quotations) return clone(mock.quotations);
  return getJson("/quotations");
}

export async function getQuotationDetail(id) {
  if (USE_MOCKS.quotationDetail) {
    const quotation = mock.quotations.find((item) => item.id === Number(id));
    const lines = mock.quotation_lines.filter((item) => item.quotation_id === Number(id));
    return { quotation: clone(quotation), lines: clone(lines) };
  }
  return getJson(`/quotations/${id}`);
}

export async function getApprovals() {
  if (USE_MOCKS.approvals) return clone(mock.approvals);
  return getJson("/approvals");
}

export async function getApprovalDetail(id) {
  if (USE_MOCKS.approvalDetail) {
    const approval = mock.approvals.find((item) => item.id === Number(id));
    const quotation = mock.quotations.find((item) => item.id === approval?.quotation_id);
    const lines = mock.quotation_lines.filter((item) => item.quotation_id === approval?.quotation_id);
    return { approval: clone(approval), quotation: clone(quotation), lines: clone(lines) };
  }
  return getJson(`/approvals/${id}`);
}

export async function getWarehouses() {
  if (USE_MOCKS.warehouses) return clone(mock.warehouses);
  return getJson("/warehouses");
}

export async function getFulfillmentDetail(quotationId) {
  if (USE_MOCKS.fulfillment) {
    const quotation = mock.quotations.find((item) => item.id === Number(quotationId));
    const lines = mock.quotation_lines.filter((item) => item.quotation_id === Number(quotationId));
    const fulfillment = mock.fulfillment_splits.find((item) => item.quotation_id === Number(quotationId));
    return { quotation: clone(quotation), lines: clone(lines), fulfillment: clone(fulfillment), warehouses: clone(mock.warehouses) };
  }
  return getJson(`/fulfillment/${quotationId}`);
}

export async function getSubscriptions() {
  if (USE_MOCKS.subscriptions) return clone(mock.subscriptions);
  return getJson("/subscriptions");
}

export async function getInvoices() {
  if (USE_MOCKS.invoices) return clone(mock.invoices);
  return getJson("/invoices");
}

export async function getInvoiceDetail(id) {
  if (USE_MOCKS.invoiceDetail) {
    const invoice = mock.invoices.find((item) => item.id === Number(id));
    const quotation = mock.quotations.find((item) => item.id === invoice?.quotation_id);
    const lines = mock.quotation_lines.filter((item) => item.quotation_id === invoice?.quotation_id);
    return { invoice: clone(invoice), quotation: clone(quotation), lines: clone(lines) };
  }
  return getJson(`/invoices/${id}`);
}

export async function getNegotiationRequests(quotationId) {
  if (USE_MOCKS.negotiationRequests) return clone(mock.negotiation_requests.filter((item) => item.quotation_id === Number(quotationId)));
  return getJson(`/negotiation-requests?quotation_id=${quotationId}`);
}

export async function getDiscountTiers() {
  if (USE_MOCKS.discountTiers) return clone(mock.discount_tiers);
  return getJson("/discount-tiers");
}

// Write actions are intentionally local-only in this hackathon frontend.
// Swap these implementations for POST/PATCH calls when backend endpoints exist.
export async function saveQuotationLineDiscount(lineId, discountPct) {
  return { id: Number(lineId), discount_pct: Number(discountPct) };
}
export async function decideApproval(approvalId, action, note = "") {
  return { id: Number(approvalId), action, note, saved: false, reason: "No approval write endpoint wired in mock-only frontend." };
}
export async function saveFulfillmentSplit(quotationId, splits) {
  return { quotation_id: Number(quotationId), splits, saved: false, reason: "No fulfillment write endpoint wired in mock-only frontend." };
}
export async function submitNegotiationRequest(payload) {
  return { ...payload, id: Date.now(), status: "pending", created_at: new Date().toISOString(), saved: false };
}
