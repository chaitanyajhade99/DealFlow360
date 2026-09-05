export const quotations = [
  { id: 1042, customer_name: "Acme Corp", customer_tier: "Gold", status: "pending_approval", created_at: "2026-09-04T10:30:00Z" },
  { id: 1041, customer_name: "Northstar Health", customer_tier: "Silver", status: "approved", created_at: "2026-09-03T15:20:00Z" },
  { id: 1039, customer_name: "Vertex Labs", customer_tier: "Bronze", status: "draft", created_at: "2026-09-02T09:15:00Z" },
  { id: 1037, customer_name: "BluePeak Retail", customer_tier: "Gold", status: "fulfillment", created_at: "2026-08-30T13:40:00Z" },
  { id: 1034, customer_name: "Kiteworks", customer_tier: "Silver", status: "confirmed", created_at: "2026-08-29T11:10:00Z" }
];

export const quotation_lines = [
  { id: 1, quotation_id: 1042, product_id: "LAPTOP-PRO-14", category: "Hardware", qty: 20, unit_price: 1400, discount_pct: 18, category_limit_pct: 15 },
  { id: 2, quotation_id: 1042, product_id: "CARE-PLAN-2YR", category: "Services", qty: 20, unit_price: 240, discount_pct: 8, category_limit_pct: 10 },
  { id: 3, quotation_id: 1042, product_id: "DOCK-USB-C", category: "Hardware", qty: 20, unit_price: 160, discount_pct: 12, category_limit_pct: 15 },
  { id: 4, quotation_id: 1041, product_id: "EDGE-SWITCH-24", category: "Hardware", qty: 8, unit_price: 620, discount_pct: 10, category_limit_pct: 15 },
  { id: 5, quotation_id: 1037, product_id: "CARE-PLAN-2YR", category: "Services", qty: 35, unit_price: 240, discount_pct: 7, category_limit_pct: 10 }
];

export const discount_tiers = [
  { id: 1, name: "Bronze", max_discount_pct: 5, category_limits: { Hardware: 5, Services: 5, Subscription: 5 }, approval_chain: { LOW: "none", MEDIUM: "sales_manager", HIGH: "sales_manager_then_finance" } },
  { id: 2, name: "Silver", max_discount_pct: 10, category_limits: { Hardware: 10, Services: 10, Subscription: 10 }, approval_chain: { LOW: "none", MEDIUM: "sales_manager", HIGH: "sales_manager_then_finance" } },
  { id: 3, name: "Gold", max_discount_pct: 15, category_limits: { Hardware: 15, Services: 10, Subscription: 10 }, approval_chain: { LOW: "none", MEDIUM: "sales_manager", HIGH: "sales_manager_then_finance" } }
];

export const approvals = [
  {
    id: 501, quotation_id: 1042, blended_risk: "HIGH", stage: "finance", assigned_to: "Maya Chen",
    history: [
      { user: "Jordan Lee", action: "submit", note: "Quote submitted for review.", at: "2026-09-04T10:30:00Z" },
      { user: "Maya Chen", action: "approve", note: "Sales manager approved; finance review required.", at: "2026-09-04T12:10:00Z" }
    ]
  },
  {
    id: 500, quotation_id: 1041, blended_risk: "MEDIUM", stage: "confirmed", assigned_to: "Maya Chen",
    history: [
      { user: "Jordan Lee", action: "submit", note: "Submitted.", at: "2026-09-03T15:20:00Z" },
      { user: "Maya Chen", action: "approve", note: "Approved within Silver tier limits.", at: "2026-09-03T16:05:00Z" }
    ]
  },
  {
    id: 498, quotation_id: 1037, blended_risk: "LOW", stage: "confirmed", assigned_to: null,
    history: [
      { user: "Jordan Lee", action: "approve", note: "No approval required.", at: "2026-08-30T13:42:00Z" }
    ]
  }
];

export const warehouses = [
  { id: 1, name: "Main Warehouse", stock: [{ product_id: "LAPTOP-PRO-14", qty: 12 }, { product_id: "DOCK-USB-C", qty: 20 }, { product_id: "CARE-PLAN-2YR", qty: 100 }] },
  { id: 2, name: "East Depot", stock: [{ product_id: "LAPTOP-PRO-14", qty: 8 }, { product_id: "DOCK-USB-C", qty: 4 }, { product_id: "CARE-PLAN-2YR", qty: 50 }] },
  { id: 3, name: "West Depot", stock: [{ product_id: "LAPTOP-PRO-14", qty: 10 }, { product_id: "DOCK-USB-C", qty: 10 }, { product_id: "CARE-PLAN-2YR", qty: 25 }] }
];

export const fulfillment_splits = [
  { id: 700, quotation_id: 1037, splits: [{ warehouse_id: 1, qty: 25, cost: 180 }, { warehouse_id: 2, qty: 10, cost: 75 }] },
  { id: 701, quotation_id: 1042, splits: [{ warehouse_id: 1, qty: 12, cost: 210 }, { warehouse_id: 2, qty: 8, cost: 145 }] }
];

export const subscriptions = [
  { id: 301, customer_name: "Acme Corp", plan: "Care Plan 2yr", cycle: "Yearly", next_bill_date: "2027-01-15", status: "active" },
  { id: 302, customer_name: "Northstar Health", plan: "Support Plus", cycle: "Monthly", next_bill_date: "2026-10-01", status: "active" },
  { id: 303, customer_name: "Kiteworks", plan: "Care Plan 2yr", cycle: "Yearly", next_bill_date: "2027-03-11", status: "active" }
];

export const invoices = [
  { id: 9001, quotation_id: 1042, amount: 30640, status: "unpaid", due_date: "2026-09-30" },
  { id: 8998, quotation_id: 1037, amount: 7980, status: "paid", due_date: "2026-09-15" },
  { id: 8991, quotation_id: 1041, amount: 4464, status: "unpaid", due_date: "2026-09-20" }
];

export const negotiation_requests = [
  { id: 1001, quotation_id: 1042, quotation_line_id: 1, customer_user_id: 41, message: "Could you sharpen the laptop discount for the first 20 units?", counter_discount_pct: 21, status: "pending", created_at: "2026-09-05T08:40:00Z" },
  { id: 1002, quotation_id: 1042, quotation_line_id: null, customer_user_id: 41, message: "We can confirm this week if the revised commercial terms work.", counter_discount_pct: null, status: "pending", created_at: "2026-09-05T08:42:00Z" }
];

export const users = [
  { id: 1, name: "Jordan Lee", email: "jordan@dealflow360.test", password_hash: "mock", role: "sales_rep", created_at: "2026-01-02T09:00:00Z" },
  { id: 2, name: "Maya Chen", email: "maya@dealflow360.test", password_hash: "mock", role: "sales_manager", created_at: "2026-01-02T09:00:00Z" }
];

export const customers = [
  { id: 11, name: "Acme Corp", default_tier: "Gold", created_at: "2026-01-01T09:00:00Z" },
  { id: 12, name: "Northstar Health", default_tier: "Silver", created_at: "2026-01-01T09:00:00Z" }
];

export const customer_users = [
  { id: 41, customer_id: 11, email: "buyer@acme.test", password_hash: null, auth_method: "magic_link", created_at: "2026-01-05T09:00:00Z" }
];

export const products = [
  { id: 101, product_code: "LAPTOP-PRO-14", name: "Laptop Pro 14", category: "Hardware", price: 1400, unit: "each", tax_pct: 8, description: "14-inch business laptop", is_subscription: false, recurring_cycle: null, quantity_on_hand: 30 },
  { id: 102, product_code: "DOCK-USB-C", name: "USB-C Dock", category: "Hardware", price: 160, unit: "each", tax_pct: 8, description: "Universal USB-C dock", is_subscription: false, recurring_cycle: null, quantity_on_hand: 34 },
  { id: 103, product_code: "CARE-PLAN-2YR", name: "Care Plan 2yr", category: "Services", price: 240, unit: "seat", tax_pct: 0, description: "Two-year support coverage", is_subscription: true, recurring_cycle: "Yearly", quantity_on_hand: null }
];

export const product_variants = [];
export const price_lists = [];
export const subscription_plans = [
  { id: 1, name: "Care Plan 2yr", cycle: "Yearly", proration_rule: { type: "daily" }, cancellation_rule: { type: "credit_note" } }
];
export const upsell_rules = [
  { id: 1, source_product_id: 101, suggested_product_id: 102, is_promoted: true, min_margin_pct: 20 },
  { id: 2, source_product_id: 101, suggested_product_id: 103, is_promoted: false, min_margin_pct: 15 }
];
export const audit_logs = [];
export const payments = [];
export const credit_notes = [];
