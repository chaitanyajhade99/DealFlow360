import { useEffect, useState } from "react";
import { Sparkles, ShieldCheck, Clock, TrendingUp } from "lucide-react";
import { getReportSummary, getQuotations } from "../../api/client";
import AdminNav from "../../components/AdminNav";
import Panel from "../../components/Panel";
import Skeleton from "../../components/Skeleton";
import StatusBadge from "../../components/StatusBadge";
import { code, date, money } from "../../utils";

export default function AdminReporting() {
  const [report, setReport] = useState(null);
  const [quotations, setQuotations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getReportSummary(), getQuotations()])
      .then(([r, q]) => {
        setReport(r);
        setQuotations(q);
      })
      .finally(() => setLoading(false));
  }, []);

  const byCategory = {};
  quotations.forEach((q) => {
    (q.lines || []).forEach((l) => {
      const net = Number(l.unit_price) * Number(l.qty) * (1 - Number(l.discount_pct) / 100);
      byCategory[l.category] = (byCategory[l.category] || 0) + net;
    });
  });

  if (loading) return <Skeleton variant="card" count={3} />;

  return (
    <div className="space-y-6 animate-fade-slide-in">
      <AdminNav />
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">Executive Governance & Ops Reporting</h1>
        <p className="mt-1 text-xs text-slate-500">Live pipeline metrics, computed from real quotation and approval data (PDF A7).</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-semibold"><TrendingUp className="h-3.5 w-3.5 text-brand-600" /> Quotes Created</div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">{report?.quotes_created ?? 0}</div>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-semibold"><Clock className="h-3.5 w-3.5 text-emerald-600" /> Avg Approval Turnaround</div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">{report?.avg_approval_time_hours != null ? `${report.avg_approval_time_hours} hrs` : "—"}</div>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-semibold"><Sparkles className="h-3.5 w-3.5 text-amber-500" /> Top Discounted Product</div>
          <div className="mt-2 text-lg font-bold text-slate-900 truncate">{report?.top_discounted_product || "—"}</div>
        </div>
      </div>

      <Panel title="Revenue by Category (net of discounts, current pipeline)">
        <div className="space-y-2.5">
          {Object.entries(byCategory).length ? (
            Object.entries(byCategory).map(([cat, val]) => (
              <div key={cat} className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">{cat}</span>
                <span className="font-mono font-bold text-slate-900">{money(val)}</span>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400">No line data yet.</p>
          )}
        </div>
      </Panel>

      <Panel title="All Quotations" right={<span className="flex items-center gap-1 text-[11px] text-slate-500"><ShieldCheck className="h-3 w-3" /> {quotations.length} total</span>}>
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead><tr><th>Quotation</th><th>Customer</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {quotations.map((q) => (
                <tr key={q.id}>
                  <td className="font-mono text-xs font-bold text-brand-700">{code("Q", q.id)}</td>
                  <td className="text-xs font-semibold text-slate-800">{q.customer_name}</td>
                  <td><StatusBadge value={q.status} /></td>
                  <td className="text-xs text-slate-500 font-mono">{date(q.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
