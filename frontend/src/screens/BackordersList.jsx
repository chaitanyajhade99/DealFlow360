import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { getBackorders } from "../api/client";
import ListScreen from "../components/ListScreen";
import StatusBadge from "../components/StatusBadge";
import { code, date } from "../utils";

// PDF section 3: Finance/Operations "manages warehouse fulfillment splits
// and backorder decisions" -- deciding what to do about a shortfall needs a
// book-wide view, not just whatever one quotation's Fulfillment tab happens
// to show. This is that view: every open (unresolved) backorder across
// every quotation, backed by the persisted Backorder table (a restock or an
// "Accept Suggested Split" that finds enough stock elsewhere clears a row
// out of this list automatically -- see api/fulfillment.py).
export default function BackordersList() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBackorders()
      .then(setRows)
      .finally(() => setLoading(false));
  }, []);

  return (
    <ListScreen
      title="Open Backorders"
      subtitle="Every quotation currently short on stock, across all warehouses, until it's resolved by a restock or a re-run allocation."
      banner={{
        title: rows.length ? `${rows.length} shortfall(s) awaiting resolution:` : "No open backorders:",
        body: rows.length
          ? "Receive stock against the affected warehouse (Admin → Warehouses) or open the quotation's Fulfillment tab to re-run the allocation once more units are available."
          : "Every quotation currently has full stock coverage.",
      }}
      columns={[
        { key: "quotation_id", label: "Quotation" },
        { key: "customer_name", label: "Customer" },
        { key: "product_id", label: "Product" },
        { key: "qty", label: "Units Short" },
        { key: "quotation_status", label: "Quotation Status" },
        { key: "created_at", label: "Open Since" },
      ]}
      rows={loading ? [] : rows}
      renderCell={(row, col) =>
        col.key === "quotation_id" ? (
          <button
            className="font-bold text-brand-700 hover:text-brand-900 hover:underline flex items-center gap-1 group font-mono text-xs"
            onClick={() => navigate(`/app/fulfillment/${row.quotation_id}`)}
            aria-label={`Open fulfillment for quotation ${code("Q", row.quotation_id)}`}
          >
            <span>{code("Q", row.quotation_id)}</span>
            <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        ) : col.key === "product_id" ? (
          <span className="font-mono text-xs text-slate-700">{row.product_id}</span>
        ) : col.key === "qty" ? (
          <span className="font-mono text-xs font-bold text-rose-700">{row.qty} unit(s)</span>
        ) : col.key === "quotation_status" ? (
          <StatusBadge value={row.quotation_status} />
        ) : col.key === "created_at" ? (
          <span className="text-slate-500 text-xs">{date(row.created_at)}</span>
        ) : (
          <span className="font-medium text-slate-800">{row[col.key]}</span>
        )
      }
    />
  );
}
