import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutList,
  Columns3,
  Plus,
  ArrowRight,
  Sparkles,
  Building,
  Calendar,
} from "lucide-react";
import { getQuotations } from "../api/client";
import ListScreen from "../components/ListScreen";
import StatusBadge from "../components/StatusBadge";
import { code, date } from "../utils";

const KANBAN_STAGES = [
  { id: "draft", label: "Draft", color: "border-slate-300 bg-slate-50/50" },
  { id: "pending_approval", label: "Pending Approval", color: "border-amber-300 bg-amber-50/30" },
  { id: "approved", label: "Approved", color: "border-emerald-300 bg-emerald-50/30" },
  { id: "fulfillment", label: "Fulfillment", color: "border-sky-300 bg-sky-50/30" },
  { id: "confirmed", label: "Confirmed", color: "border-emerald-300 bg-emerald-50/30" },
];

export default function QuotationsList() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");
  const [viewMode, setViewMode] = useState("table"); // "table" | "kanban"

  useEffect(() => {
    getQuotations().then(setRows);
  }, []);

  const filtered = useMemo(
    () => (filter === "all" ? rows : rows.filter((r) => r.status === filter)),
    [rows, filter]
  );

  return (
    <div className="space-y-4">
      {/* View Toggle Bar */}
      <div className="flex items-center justify-end gap-1.5 -mb-2">
        <div className="flex items-center rounded-lg bg-slate-100 p-0.5 border border-slate-200">
          <button
            onClick={() => setViewMode("table")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
              viewMode === "table"
                ? "bg-white text-brand-700 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
            aria-label="Table View"
          >
            <LayoutList className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Table</span>
          </button>
          <button
            onClick={() => setViewMode("kanban")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
              viewMode === "kanban"
                ? "bg-white text-brand-700 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
            aria-label="Kanban View"
          >
            <Columns3 className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Kanban</span>
          </button>
        </div>
      </div>

      {viewMode === "table" ? (
        <ListScreen
          title="Quotations (List)"
          subtitle="Review, audit discounts, and govern commercial quotations across customer tiers."
          filters={[
            { value: "all", label: "All Quotes" },
            { value: "draft", label: "Draft" },
            { value: "pending_approval", label: "Pending Approval" },
            { value: "approved", label: "Approved" },
            { value: "confirmed", label: "Confirmed" },
          ]}
          activeFilter={filter}
          onFilterChange={setFilter}
          action={
            <button
              className="df-btn-primary"
              onClick={() => navigate("/app/quotations/1042")}
              aria-label="Create new quotation"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              <span>New Quotation</span>
            </button>
          }
          banner={{
            title: "Discount guardrails active:",
            body: "Line discounts are automatically evaluated against snapshotted category limits prior to approval submission.",
          }}
          columns={[
            { key: "id", label: "Quotation" },
            { key: "customer_name", label: "Customer" },
            { key: "customer_tier", label: "Tier" },
            { key: "status", label: "Status" },
            { key: "created_at", label: "Created Date" },
          ]}
          rows={filtered}
          renderCell={(row, col) =>
            col.key === "id" ? (
              <button
                className="font-bold text-brand-700 hover:text-brand-900 hover:underline flex items-center gap-1 group font-mono text-xs"
                onClick={() => navigate(`/app/quotations/${row.id}`)}
                aria-label={`Open quotation ${code("Q", row.id)}`}
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
      ) : (
        /* Kanban Board View */
        <section className="space-y-4 animate-fade-slide-in">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">Quotations Pipeline (Kanban)</h1>
              <p className="mt-1 text-xs text-slate-500">Visual stage progression of customer deals.</p>
            </div>
            <button
              className="df-btn-primary"
              onClick={() => navigate("/app/quotations/1042")}
              aria-label="Create new quotation"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              <span>New Quotation</span>
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 overflow-x-auto pb-4 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 min-w-[700px]">
            {KANBAN_STAGES.map((stage) => {
              const stageRows = rows.filter((r) => r.status === stage.id);
              return (
                <div
                  key={stage.id}
                  className={`rounded-xl border ${stage.color} p-3.5 flex flex-col min-h-[360px] shadow-xs`}
                >
                  <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-200/80">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      {stage.label}
                    </span>
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white text-[11px] font-bold text-slate-600 border border-slate-200 shadow-xs">
                      {stageRows.length}
                    </span>
                  </div>

                  <div className="space-y-2.5 flex-1">
                    {stageRows.map((q, idx) => (
                      <div
                        key={q.id}
                        onClick={() => navigate(`/app/quotations/${q.id}`)}
                        className={`cursor-pointer rounded-lg border border-slate-200/90 bg-white p-3 shadow-xs transition-all duration-150 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover group animate-stagger-${
                          (idx % 5) + 1
                        }`}
                        role="button"
                        tabIndex={0}
                        aria-label={`Open quotation ${code("Q", q.id)} for ${q.customer_name}`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs font-bold text-brand-700 group-hover:underline">
                            {code("Q", q.id)}
                          </span>
                          <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 rounded px-1.5 py-0.5">
                            {q.customer_tier}
                          </span>
                        </div>
                        <div className="mt-2 text-xs font-bold text-slate-800 line-clamp-1 flex items-center gap-1">
                          <Building className="h-3 w-3 text-slate-400" />
                          {q.customer_name}
                        </div>
                        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3 text-slate-300" />
                            {date(q.created_at)}
                          </span>
                          <StatusBadge value={q.status} />
                        </div>
                      </div>
                    ))}
                    {stageRows.length === 0 && (
                      <div className="h-24 rounded-lg border border-dashed border-slate-200 flex items-center justify-center text-[11px] text-slate-400">
                        No quotes in {stage.label}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

