export const money = (value) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0));
export const pct = (value) => `${Number(value || 0).toFixed(1)}%`;
export const date = (value) => value ? new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";
export const code = (prefix, id) => `${prefix}-${String(id).padStart(4, "0")}`;
export const lineTotal = (line, discount = line.discount_pct) => Number(line.qty) * Number(line.unit_price) * (1 - Number(discount || 0) / 100);
export const riskFor = (discount, limit) => Number(discount) > Number(limit) ? "HIGH" : Number(discount) > Number(limit) * 0.8 ? "MEDIUM" : "LOW";

const RAZORPAY_SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js";

export function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = RAZORPAY_SCRIPT_URL;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}
