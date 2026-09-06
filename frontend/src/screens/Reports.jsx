import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Filter, TrendingUp, Clock, Sparkles, Download } from "lucide-react";
import { getReportSummary, exportReportPdf, exportReportXlsx } from "../api/client";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, date } from "../utils";

export default function Reports() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [filters, setFilters] = useState({ date_from: "", date_to: "", approval_status: "", category: "" });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(null);

  const activeParams = () => Object.fromEntries(Object.entries(filters).filter(([, v]) => v));

  const handleExport = async (kind) => {
    setExporting(kind);
    try {
      await (kind === "pdf" ? exportReportPdf(activeParams()) : exportReportXlsx(activeParams()));
    } catch (err) {
      toast(err.message || "Could not generate export.", "error");
    } finally {
      setExporting(null);
    }
  };

  const load = (f) => {
    setLoading(true);
    const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
    getReportSummary(params)
      .then(setReport)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyFilters = (e) => {
    e.preventDefault();
    load(filters);
  };

  return (
    <div className="space-y-6 animate-fade-slide-in">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Reports & Analytics</h1>
          <p className="mt-1 text-xs text-slate-500">Live pipeline metrics filtered by period, approval status, and category (PDF A7).</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={() => handleExport("pdf")} disabled={exporting} className="df-btn-secondary gap-1.5 text-xs">
            <Download className="h-3.5 w-3.5" /> {exporting === "pdf" ? "Exporting..." : "Export PDF"}
          </button>
          <button onClick={() => handleExport("xlsx")} disabled={exporting} className="df-btn-secondary gap-1.5 text-xs">
            <Download className="h-3.5 w-3.5" /> {exporting === "xlsx" ? "Exporting..." : "Export XLS"}
          </button>
        </div>
      </div>

      <form onSubmit={applyFilters} className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
        <div className="flex items-center gap-2 mb-3 text-xs font-bold text-slate-700">
          <Filter className="h-3.5 w-3.5 text-brand-600" />
          <span>Filters</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label className="df-label">From</label>
            <input type="date" className="df-input text-xs" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
          </div>
          <div>
            <label className="df-label">To</label>
            <input type="date" className="df-input text-xs" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
          </div>
          <div>
            <label className="df-label">Approval Status</label>
            <select className="df-input text-xs" value={filters.approval_status} onChange={(e) => setFilters({ ...filters, approval_status: e.target.value })}>
              <option value="">All</option>
              <option value="pending_approval">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="confirmed">Confirmed</option>
            </select>
          </div>
          <div>
            <label className="df-label">Category</label>
            <select className="df-input text-xs" value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })}>
              <option value="">All</option>
              <option value="Hardware">Hardware</option>
              <option value="Services">Services</option>
              <option value="Subscription">Subscription</option>
            </select>
          </div>
          <div className="flex items-end">
            <button type="submit" className="df-btn-primary text-xs w-full">Apply Filters</button>
          </div>
        </div>
      </form>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-3"><Skeleton variant="card" /><Skeleton variant="card" /><Skeleton variant="card" /></div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <TrendingUp className="h-3.5 w-3.5 text-brand-600" /> Quotes Created
            </div>
            <div className="mt-2 text-2xl font-black text-slate-900 font-mono">{report?.quotes_created ?? 0}</div>
          </div>
          <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <Clock className="h-3.5 w-3.5 text-emerald-600" /> Avg Approval Time
            </div>
            <div className="mt-2 text-2xl font-black text-slate-900 font-mono">
              {report?.avg_approval_time_hours != null ? `${report.avg_approval_time_hours} hrs` : "—"}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <Sparkles className="h-3.5 w-3.5 text-amber-500" /> Top Discounted Product
            </div>
            <div className="mt-2 text-lg font-bold text-slate-900 truncate">{report?.top_discounted_product || "—"}</div>
          </div>
        </div>
      )}

      <Panel title="Matching Quotations" right={<span className="text-[11px] text-slate-400">{report?.matching_quotations?.length ?? 0} results</span>}>
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Quotation</th>
                <th>Customer</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {(report?.matching_quotations || []).map((q) => (
                <tr key={q.id}>
                  <td>
                    <button onClick={() => navigate(`/app/quotations/${q.id}`)} className="font-mono text-xs font-bold text-brand-700 hover:underline">
                      {code("Q", q.id)}
                    </button>
                  </td>
                  <td className="text-xs font-semibold text-slate-800">{q.customer_name}</td>
                  <td><StatusBadge value={q.status} /></td>
                  <td className="text-xs text-slate-500 font-mono">{date(q.created_at)}</td>
                </tr>
              ))}
              {!report?.matching_quotations?.length && (
                <tr><td colSpan={4} className="text-center text-xs text-slate-400 py-6">No quotations match these filters.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-[11px] text-slate-500">
Export PDF/XLS above downloads exactly this filtered result set (same query the summary above is built from). Every number is live from the backend.
      </div>
    </div>
  );
}
