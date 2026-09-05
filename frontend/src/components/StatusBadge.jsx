const map = {
  draft: { bg: "bg-slate-100 text-slate-700 border border-slate-200", dot: "bg-slate-400", label: "Draft" },
  pending_approval: { bg: "bg-amber-50 text-amber-800 border border-amber-200/80", dot: "bg-amber-500", label: "Pending approval" },
  approved: { bg: "bg-emerald-50 text-emerald-800 border border-emerald-200/80", dot: "bg-emerald-500", label: "Approved" },
  confirmed: { bg: "bg-emerald-50 text-emerald-800 border border-emerald-200/80", dot: "bg-emerald-500", label: "Confirmed" },
  fulfillment: { bg: "bg-sky-50 text-sky-800 border border-sky-200/80", dot: "bg-sky-500", label: "Fulfillment" },
  invoiced: { bg: "bg-indigo-50 text-indigo-800 border border-indigo-200/80", dot: "bg-indigo-500", label: "Invoiced" },
  paid: { bg: "bg-emerald-50 text-emerald-800 border border-emerald-200/80", dot: "bg-emerald-500", label: "Paid" },
  cancelled: { bg: "bg-rose-50 text-rose-800 border border-rose-200/80", dot: "bg-rose-500", label: "Cancelled" },
  unpaid: { bg: "bg-amber-50 text-amber-800 border border-amber-200/80", dot: "bg-amber-500", label: "Unpaid" },
  active: { bg: "bg-emerald-50 text-emerald-800 border border-emerald-200/80", dot: "bg-emerald-500", label: "Active" },
  HIGH: { bg: "bg-red-50 text-red-800 border border-red-200/80", dot: "bg-red-500", label: "High risk" },
  MEDIUM: { bg: "bg-amber-50 text-amber-800 border border-amber-200/80", dot: "bg-amber-500", label: "Medium risk" },
  LOW: { bg: "bg-emerald-50 text-emerald-800 border border-emerald-200/80", dot: "bg-emerald-500", label: "Low risk" },
  pending: { bg: "bg-amber-50 text-amber-800 border border-amber-200/80", dot: "bg-amber-500", label: "Pending" },
  rejected: { bg: "bg-rose-50 text-rose-800 border border-rose-200/80", dot: "bg-rose-500", label: "Rejected" },
  returned: { bg: "bg-orange-50 text-orange-800 border border-orange-200/80", dot: "bg-orange-500", label: "Returned" },
  resolved: { bg: "bg-emerald-50 text-emerald-800 border border-emerald-200/80", dot: "bg-emerald-500", label: "Resolved" },
};

export default function StatusBadge({ value, className = "" }) {
  const item = map[value] || {
    bg: "bg-slate-100 text-slate-700 border border-slate-200",
    dot: "bg-slate-400",
    label: String(value || "—").replaceAll("_", " "),
  };

  return (
    <span className={`df-badge ${item.bg} ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${item.dot}`} aria-hidden="true" />
      <span>{item.label}</span>
    </span>
  );
}

