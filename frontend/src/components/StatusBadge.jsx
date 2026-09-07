/* QuoteIt — Status badge with dot indicator */

const STATUS_MAP = {
  // Quotation statuses
  draft:            { cls: "bg-slate-100 text-slate-700 border-slate-200",  dot: "bg-slate-400",  label: "Draft" },
  pending_approval: { cls: "bg-amber-50  text-amber-800  border-amber-200",  dot: "bg-amber-500",  label: "Pending Approval" },
  approved:         { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500", label: "Approved" },
  confirmed:        { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500", label: "Confirmed" },
  negotiation:      { cls: "bg-indigo-50 text-indigo-800 border-indigo-200",  dot: "bg-indigo-500", label: "Negotiation" },
  fulfillment:      { cls: "bg-sky-50    text-sky-800    border-sky-200",     dot: "bg-sky-500",    label: "Fulfillment" },
  invoiced:         { cls: "bg-violet-50 text-violet-800 border-violet-200",  dot: "bg-violet-500", label: "Invoiced" },
  paid:             { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500", label: "Paid" },
  cancelled:        { cls: "bg-rose-50   text-rose-800   border-rose-200",    dot: "bg-rose-500",   label: "Cancelled" },
  rejected:         { cls: "bg-rose-50   text-rose-800   border-rose-200",    dot: "bg-rose-500",   label: "Rejected" },
  returned:         { cls: "bg-orange-50 text-orange-800 border-orange-200",  dot: "bg-orange-500", label: "Returned" },
  // Invoice/payment
  unpaid:           { cls: "bg-amber-50  text-amber-800  border-amber-200",   dot: "bg-amber-500",  label: "Unpaid" },
  // Subscription
  active:           { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500", label: "Active" },
  pending:          { cls: "bg-amber-50  text-amber-800  border-amber-200",   dot: "bg-amber-500",  label: "Pending" },
  resolved:         { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500", label: "Resolved" },
  // Risk level
  HIGH:    { cls: "bg-red-50     text-red-800    border-red-200",    dot: "bg-red-500",    label: "High Risk" },
  MEDIUM:  { cls: "bg-amber-50   text-amber-800  border-amber-200",  dot: "bg-amber-500",  label: "Medium Risk" },
  LOW:     { cls: "bg-emerald-50 text-emerald-800 border-emerald-200", dot: "bg-emerald-500", label: "Low Risk" },
};

export default function StatusBadge({ value, className = "" }) {
  const item = STATUS_MAP[value] || {
    cls: "bg-slate-100 text-slate-700 border-slate-200",
    dot: "bg-slate-400",
    label: String(value || "—").replaceAll("_", " "),
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-semibold ${item.cls} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${item.dot} shrink-0`} aria-hidden="true" />
      <span className="capitalize">{item.label}</span>
    </span>
  );
}
