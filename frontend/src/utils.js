export const money = (value) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(Number(value || 0));
export const pct = (value) => `${Number(value || 0).toFixed(1)}%`;
export const date = (value) => value ? new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";
export const code = (prefix, id) => `${prefix}-${String(id).padStart(4, "0")}`;
export const lineTotal = (line, discount = line.discount_pct) => Number(line.qty) * Number(line.unit_price) * (1 - Number(discount || 0) / 100);
export const riskFor = (discount, limit) => Number(discount) > Number(limit) ? "HIGH" : Number(discount) > Number(limit) * 0.8 ? "MEDIUM" : "LOW";
