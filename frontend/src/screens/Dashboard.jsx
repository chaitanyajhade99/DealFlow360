import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Clock,
  FileText,
  AlertTriangle,
  ChevronRight,
  ArrowUpRight,
  Info,
} from "lucide-react";
import { getDashboardSummary } from "../api/client";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { date } from "../utils";

export default function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboardSummary(12)
      .then((data) => {
        setSummary(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load dashboard");
        setLoading(false);
      });
  }, []);

  const cards = [
    {
      key: "pending_approvals",
      label: "Pending Approvals",
      icon: Clock,
      iconClass: "text-amber-500",
      hint: "Awaiting manager/finance",
      onClick: () => navigate("/app/approvals"),
    },
    {
      key: "open_quotations",
      label: "Open Quotations",
      icon: FileText,
      iconClass: "text-brand-500",
      hint: "Draft, review & active",
      onClick: () => navigate("/app/quotations"),
    },
    {
      key: "at_risk_deals",
      label: "At-Risk Deals",
      icon: AlertTriangle,
      iconClass: "text-red-500",
      hint: "Stalled, anomalous, or slipping",
      onClick: () => navigate("/app/deal-health"),
    },
  ];

  return (
    <section className="space-y-5 animate-fade-slide-in">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-xl font-black tracking-tight text-slate-900 flex items-center gap-2">
            Sales Dashboard
            <span className="rounded-md bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700 border border-brand-200/60">
              Live
            </span>
          </h1>
          <p className="mt-0.5 text-xs text-slate-500">
            Real-time pipeline health, pending governance queues, and deal risk analytics.
          </p>
        </div>
        <button onClick={() => navigate("/app/quotations/new")} className="df-btn-primary" aria-label="Create new quotation">
          <span>+ New Quotation</span>
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-800">
          Could not reach the backend at the configured API URL: {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(({ key, label, icon: Icon, iconClass, hint, onClick }) => (
          <div
            key={key}
            onClick={onClick}
            className="group cursor-pointer rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover"
            role="button"
            tabIndex={0}
            aria-label={`View ${label}`}
          >
            <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
              <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
                <Icon className={`h-3.5 w-3.5 ${iconClass}`} aria-hidden="true" />
                {label}
              </span>
              <ArrowUpRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-brand-600 transition-colors" />
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <div>
                <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {loading ? <Skeleton variant="title" className="w-12" /> : summary?.[key] ?? 0}
                </div>
                <p className="mt-0.5 text-[11px] font-medium text-slate-500">{hint}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Panel
        title="Recent Activity"
        right={<span className="text-[11px] text-slate-400">Live from audit log, approvals & negotiations</span>}
      >
        {loading ? (
          <Skeleton variant="tableRow" count={5} />
        ) : summary?.recent_activity?.length ? (
          <div className="divide-y divide-slate-100">
            {summary.recent_activity.map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2.5 text-xs">
                <span className="text-slate-700">{item.description}</span>
                <span className="text-slate-400 font-mono text-[11px] shrink-0 ml-3">{date(item.at)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 py-4 text-center">No activity yet.</p>
        )}
      </Panel>

      <div className="flex items-start gap-3 rounded-lg border border-amber-300/80 bg-amber-50/90 px-4 py-3 text-xs text-amber-900 shadow-xs">
        <Info className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" aria-hidden="true" />
        <div>
          <span className="font-bold">End-to-End Pipeline Workflow:</span>
          <span className="ml-1 text-amber-800">
            Quotes move from <b>Quotations</b> → <b>Approval</b> → <b>Fulfillment</b> →{" "}
            <b>Invoices & Payments</b>. Customer negotiations occur in the separate portal shell and
            <ChevronRight className="inline h-3 w-3 mx-0.5" /> automatically re-enter approval when terms change.
          </span>
        </div>
      </div>
    </section>
  );
}
