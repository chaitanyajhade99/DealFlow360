import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Truck, Boxes } from "lucide-react";
import { getQuotations } from "../api/client";
import ListScreen from "../components/ListScreen";
import StatusBadge from "../components/StatusBadge";
import { code, date } from "../utils";

export default function FulfillmentList() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");
  const navigate = useNavigate();

  useEffect(() => {
    getQuotations().then((q) =>
      setRows(q.filter((x) => ["approved", "confirmed"].includes(x.status)))
    );
  }, []);

  const filtered = useMemo(
    () => (filter === "all" ? rows : rows.filter((r) => r.status === filter)),
    [rows, filter]
  );

  return (
    <ListScreen
      title="Fulfillment and Stock Allocation (List)"
      subtitle="Warehouse routing, inventory readiness, and multi-depot split execution."
      filters={[
        { value: "all", label: "All Active" },
        { value: "approved", label: "Approved" },
        { value: "confirmed", label: "Confirmed Orders" },
      ]}
      activeFilter={filter}
      onFilterChange={setFilter}
      banner={{
        title: "Algorithmic warehouse allocation active:",
        body: "Suggested multi-depot inventory splits minimize shipping cost. Use 'Manual Override' to adjust quantities.",
      }}
      columns={[
        { key: "id", label: "Quotation Ref" },
        { key: "customer_name", label: "Customer" },
        { key: "customer_tier", label: "Customer Tier" },
        { key: "status", label: "Fulfillment Status" },
        { key: "created_at", label: "Order Date" },
      ]}
      rows={filtered}
      renderCell={(row, col) =>
        col.key === "id" ? (
          <button
            className="font-bold text-brand-700 hover:text-brand-900 hover:underline flex items-center gap-1 group font-mono text-xs"
            onClick={() => navigate(`/app/fulfillment/${row.id}`)}
            aria-label={`Open fulfillment order ${code("Q", row.id)}`}
          >
            <span>{code("Q", row.id)}</span>
            <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        ) : col.key === "status" ? (
          <StatusBadge value={row.status} />
        ) : col.key === "customer_tier" ? (
          <span className="font-semibold text-slate-700">{row.customer_tier}</span>
        ) : col.key === "created_at" ? (
          <span className="text-slate-500 text-xs">{date(row.created_at)}</span>
        ) : (
          <span className="font-medium text-slate-800">{row[col.key]}</span>
        )
      }
    />
  );
}

