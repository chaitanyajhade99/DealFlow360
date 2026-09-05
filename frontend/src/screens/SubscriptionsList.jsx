import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import ListScreen from "../components/ListScreen";
import StatusBadge from "../components/StatusBadge";
import { getSubscriptions } from "../api/client";
import { date, money } from "../utils";

export default function SubscriptionsList() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    getSubscriptions().then(setRows);
  }, []);

  const filtered = useMemo(
    () => (filter === "all" ? rows : rows.filter((x) => x.status === filter)),
    [rows, filter]
  );

  return (
    <ListScreen
      title="Recurring Subscriptions & Maintenance (List)"
      subtitle="Lifecycle management of recurring service contracts and automated renewal cycles."
      filters={[
        { value: "all", label: "All Subscriptions" },
        { value: "active", label: "Active" },
        { value: "cancelled", label: "Cancelled" },
      ]}
      activeFilter={filter}
      onFilterChange={setFilter}
      banner={{
        title: "Hybrid billing:",
        body: "Recurring subscription lines are tracked separately from one-time invoice lines, with real mid-cycle proration on modify and prorated refunds on cancel.",
      }}
      columns={[
        { key: "id", label: "Subscription Ref" },
        { key: "customer_name", label: "Subscriber Account" },
        { key: "plan", label: "Plan Type" },
        { key: "cycle", label: "Billing Cadence" },
        { key: "amount", label: "Recurring Amount" },
        { key: "next_bill_date", label: "Next Invoice Date" },
        { key: "status", label: "Lifecycle Status" },
      ]}
      rows={filtered}
      renderCell={(row, col) =>
        col.key === "id" ? (
          <button
            className="font-bold text-brand-700 hover:text-brand-900 hover:underline flex items-center gap-1 group font-mono text-xs"
            onClick={() => navigate(`/app/billing/${row.id}`)}
            aria-label={`View billing for subscription S-${String(row.id).padStart(4, "0")}`}
          >
            <span>{`S-${String(row.id).padStart(4, "0")}`}</span>
            <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        ) : col.key === "next_bill_date" ? (
          <span className="text-slate-600 text-xs font-mono">{date(row.next_bill_date)}</span>
        ) : col.key === "cycle" ? (
          <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
            {row.cycle}
          </span>
        ) : col.key === "status" ? (
          <StatusBadge value={row.status} />
        ) : col.key === "plan" ? (
          <span className="font-semibold text-slate-800">{row.plan}</span>
        ) : col.key === "amount" ? (
          <span className="font-mono text-xs font-bold text-slate-900">{row.amount != null ? money(row.amount) : "—"}</span>
        ) : (
          <span className="font-medium text-slate-800">{row[col.key]}</span>
        )
      }
    />
  );
}

