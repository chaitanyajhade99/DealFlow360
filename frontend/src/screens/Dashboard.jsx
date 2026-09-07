import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Clock, FileText, AlertTriangle, ChevronRight, ArrowUpRight,
  TrendingUp, TrendingDown, Minus, Plus, Zap, Activity,
} from "lucide-react";
import { getDashboardSummary } from "../api/client";
import Skeleton from "../components/Skeleton";
import { date } from "../utils";

/* ─── Stat card ────────────────────────────────────────────────────── */
function StatCard({ label, value, hint, icon: Icon, iconColor, trend, onClick, loading }) {
  const trendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus;
  const trendColor = trend > 0 ? "text-emerald-600" : trend < 0 ? "text-red-500" : "text-ink-muted";

  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === "Enter" && onClick() : undefined}
      className={`qit-panel p-5 transition-all duration-150 ${
        onClick
          ? "cursor-pointer hover:shadow-sm hover:border-brand-200 hover:-translate-y-px group"
          : ""
      }`}
    >
      <div className="flex items-start justify-between">
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${iconColor}`}>
          <Icon className="h-4.5 w-4.5 h-[18px] w-[18px]" aria-hidden="true" />
        </div>
        {onClick && (
          <ArrowUpRight className="h-4 w-4 text-ink-muted group-hover:text-brand-600 transition-colors" />
        )}
      </div>

      <div className="mt-4">
        {loading ? (
          <div className="qit-skeleton h-8 w-20 rounded mb-2" />
        ) : (
          <div className="text-[28px] font-bold text-ink leading-none tabular">{value ?? 0}</div>
        )}
        <div className="qit-stat-label mt-1.5">{label}</div>
        {hint && <div className="qit-stat-hint">{hint}</div>}
      </div>

      {trend !== undefined && !loading && (
        <div className={`mt-3 flex items-center gap-1 text-[11px] font-semibold ${trendColor}`}>
          <trendIcon className="h-3 w-3" />
          {trend > 0 ? `+${trend}` : trend} from last week
        </div>
      )}
    </div>
  );
}

/* ─── Activity item ────────────────────────────────────────────────── */
function ActivityItem({ item, i }) {
  return (
    <div className={`flex items-center justify-between py-3 animate-stagger-${Math.min(i + 1, 6)}`}>
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-50 border border-brand-100">
          <Activity className="h-3 w-3 text-brand-600" />
        </div>
        <span className="text-sm text-ink-secondary truncate">{item.description}</span>
      </div>
      <span className="text-[11px] text-ink-muted font-mono shrink-0 ml-3 tabular">
        {date(item.at)}
      </span>
    </div>
  );
}

/* ─── Main Dashboard ───────────────────────────────────────────────── */
export default function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboardSummary(12)
      .then((data) => { setSummary(data); setLoading(false); })
      .catch((err) => { setError(err.message || "Failed to load dashboard"); setLoading(false); });
  }, []);

  const stats = [
    {
      key: "open_quotations",
      label: "Open Quotations",
      hint: "Draft, review & active",
      icon: FileText,
      iconColor: "bg-brand-50 text-brand-600",
      onClick: () => navigate("/app/quotations"),
    },
    {
      key: "pending_approvals",
      label: "Pending Approvals",
      hint: "Awaiting manager / finance",
      icon: Clock,
      iconColor: "bg-amber-50 text-amber-600",
      onClick: () => navigate("/app/approvals"),
    },
    {
      key: "at_risk_deals",
      label: "At-Risk Deals",
      hint: "Stalled, anomalous, or slipping",
      icon: AlertTriangle,
      iconColor: "bg-red-50 text-red-600",
      onClick: () => navigate("/app/deal-health"),
    },
  ];

  return (
    <section className="space-y-6 animate-fade-slide-in">

      {/* ── Page header ─────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="qit-page-title flex items-center gap-2">
            Sales Dashboard
            <span className="qit-badge qit-badge-green text-[10px]">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </span>
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Real-time pipeline health, pending governance queues, and deal risk analytics.
          </p>
        </div>
        <button
          onClick={() => navigate("/app/quotations/new")}
          className="qit-btn-primary shrink-0"
          aria-label="Create new quotation"
        >
          <Plus className="h-3.5 w-3.5" />
          New Quotation
        </button>
      </div>

      {/* ── Error state ─────────────────────────────────────────────── */}
      {error && (
        <div className="qit-alert qit-alert-danger">
          <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
          <div>
            <b>Backend unreachable:</b>{" "}
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* ── KPI stat cards ──────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map(({ key, ...rest }) => (
          <StatCard
            key={key}
            value={summary?.[key]}
            loading={loading}
            {...rest}
          />
        ))}
      </div>

      {/* ── Intelligence banner ──────────────────────────────────────── */}
      {!loading && (
        <div className="flex items-start gap-3 rounded-lg border border-brand-200 bg-brand-50/60 px-4 py-3.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-600">
            <Zap className="h-3.5 w-3.5 text-white" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-brand-900">QuoteIt Intelligence</div>
            <p className="text-xs text-brand-800 mt-0.5">
              Quotes move through{" "}
              <b>Quotations → Approval → Fulfillment → Invoices & Payments</b>.{" "}
              Customer negotiations in the portal automatically re-enter approval when terms change.
            </p>
          </div>
          <button
            onClick={() => navigate("/app/quotations")}
            className="shrink-0 qit-btn qit-btn-sm border border-brand-300 bg-brand-100 text-brand-700 hover:bg-brand-200"
          >
            View Pipeline <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* ── Recent activity ─────────────────────────────────────────── */}
      <div className="qit-panel">
        <div className="qit-panel-header">
          <h2 className="qit-panel-title">Recent Activity</h2>
          <span className="text-[11px] text-ink-muted">Live from audit log, approvals & negotiations</span>
        </div>
        <div className="px-5">
          {loading ? (
            <div className="space-y-3 py-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="qit-skeleton h-6 w-6 rounded-full" />
                  <div className="qit-skeleton h-4 flex-1 rounded" />
                  <div className="qit-skeleton h-3 w-20 rounded" />
                </div>
              ))}
            </div>
          ) : summary?.recent_activity?.length ? (
            <div className="divide-y divide-line-subtle">
              {summary.recent_activity.map((item, i) => (
                <ActivityItem key={i} item={item} i={i} />
              ))}
            </div>
          ) : (
            <div className="qit-empty py-10">
              <div className="qit-empty-icon">
                <Activity className="h-6 w-6" />
              </div>
              <p className="qit-empty-title">No activity yet</p>
              <p className="qit-empty-body">
                Create a quotation to start your sales pipeline.
              </p>
              <button
                onClick={() => navigate("/app/quotations/new")}
                className="qit-btn-primary mt-4"
              >
                <Plus className="h-3.5 w-3.5" /> Create First Quote
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Quick links row ─────────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { label: "Deal Health Monitor", to: "/app/deal-health", icon: Activity, desc: "Stalled, anomalies, slippage" },
          { label: "Approval Queue",      to: "/app/approvals",   icon: Clock,    desc: "Pending manager decisions" },
          { label: "Fulfillment Status",  to: "/app/fulfillment", icon: TrendingUp, desc: "Warehouse & backorder status" },
        ].map(({ label, to, icon: Icon, desc }) => (
          <button
            key={to}
            onClick={() => navigate(to)}
            className="qit-panel group flex items-center gap-3 p-4 text-left hover:border-brand-200 hover:shadow-sm transition-all duration-150 cursor-pointer"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-600 group-hover:bg-brand-100 transition-colors">
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-ink">{label}</div>
              <div className="text-[11px] text-ink-muted">{desc}</div>
            </div>
            <ArrowUpRight className="h-4 w-4 text-ink-muted group-hover:text-brand-600 transition-colors shrink-0" />
          </button>
        ))}
      </div>
    </section>
  );
}
