import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Receipt, Calendar } from "lucide-react";
import { getInvoices } from "../api/client";
import ListScreen from "../components/ListScreen";
import StatusBadge from "../components/StatusBadge";
import { code, date, money } from "../utils";

export default function InvoicesList() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");
  const navigate = useNavigate();

  useEffect(() => {
    getInvoices().then(setRows);
  }, []);

  const filtered = useMemo(
    () => (filter === "all" ? rows : rows.filter((r) => r.status === filter)),
    [rows, filter]
  );

  return (
    <ListScreen
      title="Invoices & Receivables (List)"
      subtitle="Commercial invoice status, due dates, settlement tracking, and order links."
      filters={[
        { value: "all", label: "All Invoices" },
        { value: "unpaid", label: "Unpaid / Due" },
        { value: "paid", label: "Settled / Paid" },
      ]}
      activeFilter={filter}
      onFilterChange={setFilter}
      banner={{
        title: "Invoices are auto-generated:",
        body: "An invoice is created automatically the moment a quotation is confirmed or fully approved. Recording a payment here updates the real balance and flips status to paid once covered.",
      }}
      columns={[
        { key: "id", label: "Invoice Number" },
        { key: "quotation_id", label: "Source Quote" },
        { key: "amount", label: "Total Amount Due" },
        { key: "status", label: "Payment Status" },
        { key: "due_date", label: "Payment Due Date" },
      ]}
      rows={filtered}
      renderCell={(row, col) =>
        col.key === "id" ? (
          <button
            className="font-bold text-brand-700 hover:text-brand-900 hover:underline flex items-center gap-1 group font-mono text-xs"
            onClick={() => navigate(`/app/invoices/${row.id}`)}
            aria-label={`Open invoice ${code("INV", row.id)}`}
          >
            <span>{code("INV", row.id)}</span>
            <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        ) : col.key === "quotation_id" ? (
          <button
            onClick={() => navigate(`/app/quotations/${row.quotation_id}`)}
            className="font-mono text-xs font-semibold text-slate-700 hover:text-brand-700 hover:underline"
          >
            {code("Q", row.quotation_id)}
          </button>
        ) : col.key === "amount" ? (
          <span className="font-mono font-bold text-xs text-slate-900">{money(row.amount)}</span>
        ) : col.key === "status" ? (
          <StatusBadge value={row.status} />
        ) : col.key === "due_date" ? (
          <span className="text-slate-600 text-xs font-mono">{date(row.due_date)}</span>
        ) : (
          <span className="font-medium text-slate-800">{row[col.key]}</span>
        )
      }
    />
  );
}

