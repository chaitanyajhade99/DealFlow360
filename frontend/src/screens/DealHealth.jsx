import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Clock, ShieldAlert, Truck, ArrowRight, Bell, TrendingUp,
  Activity, AlertTriangle, CheckCircle2, RefreshCcw,
} from "lucide-react";
import { getDealHealth, nudgeQuotation, escalateQuotation } from "../api/client";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, date } from "../utils";

/* ─── Alert table ──────────────────────────────────────────────────── */
function AlertTable({ rows, columns, renderRow, onNudge, onEscalate, onOpen, busyId, emptyLabel }) {
  if (!rows.length) {
    return (
      <div className="flex items-center justify-center gap-2 py-8 text-xs text-ink-muted">
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        {emptyLabel || "No alerts in this category."}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="qit-table">
        <thead>
          <tr>
            {columns.map((c) => <th key={c}>{c}</th>)}
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => {
            const cells = renderRow(r);
            const busy = busyId === r.quotation_id;
            return (
              <tr key={r.quotation_id} className={`animate-stagger-${Math.min(idx + 1, 6)}`}>
                {cells.map((c, i) => (
                  <td key={i} className={i === 0 ? "font-semibold text-ink" : "font-mono text-xs text-ink-secondary"}>
                    {c}
                  </td>
                ))}
                <td>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => onNudge(r)}
                      disabled={busy}
                      className="qit-btn qit-btn-secondary qit-btn-sm gap-1"
                      aria-label={`Nudge quotation ${r.quotation_id}`}
                    >
                      <Bell className="h-3 w-3" /> Nudge
                    </button>
                    <button
                      onClick={() => onEscalate(r)}
                      disabled={busy}
                      className="qit-btn qit-btn-sm border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 gap-1"
                      aria-label={`Escalate quotation ${r.quotation_id}`}
                    >
                      <TrendingUp className="h-3 w-3" /> Escalate
                    </button>
                    <button
                      onClick={() => onOpen(r)}
                      className="qit-btn qit-btn-secondary qit-btn-sm gap-1"
                      aria-label={`Open quotation ${r.quotation_id}`}
                    >
                      Open <ArrowRight className="h-3 w-3" />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ─── KPI summary card ─────────────────────────────────────────────── */
function HealthCard({ label, value, icon: Icon, colorClass, bgClass }) {
  return (
    <div className={`rounded-lg border ${colorClass} ${bgClass} p-5`}>
      <div className="flex items-center justify-between">
        <p className="qit-stat-label">{label}</p>
        <Icon className={`h-5 w-5 ${colorClass.replace("border-", "text-").replace("/80","")}`} aria-hidden="true" />
      </div>
      <div className="mt-3 text-3xl font-bold text-ink tabular">{value}</div>
    </div>
  );
}

/* ─── Main screen ──────────────────────────────────────────────────── */
export default function DealHealth() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setRefreshing(true);
    try {
      const data = await getDealHealth();
      setHealth(data);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const handleAction = async (fn, quotationId, label) => {
    setBusyId(quotationId);
    try {
      await fn(quotationId, {});
      toast(`${label} sent for ${code("Q", quotationId)}.`, "success");
      await load();
    } catch (err) {
      toast(err.message || "Action failed.", "error");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5 animate-fade-slide-in">
        <Skeleton variant="title" className="w-72" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton variant="stat" />
          <Skeleton variant="stat" />
          <Skeleton variant="stat" />
        </div>
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const totalAlerts = (health?.stalled_deals?.length || 0)
    + (health?.discount_anomalies?.length || 0)
    + (health?.delivery_slippage?.length || 0);

  const kpis = [
    {
      label: "Stalled Deals",
      value: health?.stalled_deals?.length ?? 0,
      icon: Clock,
      colorClass: "border-amber-200",
      bgClass: "bg-amber-50",
    },
    {
      label: "Discount Anomalies",
      value: health?.discount_anomalies?.length ?? 0,
      icon: ShieldAlert,
      colorClass: "border-red-200",
      bgClass: "bg-red-50",
    },
    {
      label: "Delivery Slippage",
      value: health?.delivery_slippage?.length ?? 0,
      icon: Truck,
      colorClass: "border-sky-200",
      bgClass: "bg-sky-50",
    },
  ];

  return (
    <section className="space-y-6 animate-fade-slide-in">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="qit-page-title flex items-center gap-2.5">
            <Activity className="h-5 w-5 text-brand-600" aria-hidden="true" />
            Deal Health Monitor
            {totalAlerts > 0 ? (
              <span className="qit-badge qit-badge-red">
                {totalAlerts} alert{totalAlerts !== 1 ? "s" : ""}
              </span>
            ) : (
              <span className="qit-badge qit-badge-green">All Clear</span>
            )}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Stalled quotes, discount anomalies (per-rep z-score), and delivery promise slippage — nudge or escalate in one click.
          </p>
        </div>
        <button
          onClick={load}
          disabled={refreshing}
          className="qit-btn-secondary shrink-0 gap-1.5"
          aria-label="Refresh deal health data"
        >
          <RefreshCcw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* ── KPI cards ──────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-3">
        {kpis.map((c) => (
          <HealthCard key={c.label} {...c} />
        ))}
      </div>

      {/* ── Stalled deals table ─────────────────────────────────────── */}
      <Panel
        title="Stalled Deals"
        right={<span className="text-[11px] text-ink-muted flex items-center gap-1.5"><Clock className="h-3 w-3" /> Inactive 5+ days</span>}
        noPad
      >
        <AlertTable
          rows={health?.stalled_deals || []}
          columns={["Customer", "Status", "Days Inactive"]}
          renderRow={(r) => [r.customer_name, r.status.replaceAll("_", " "), `${r.days_inactive}d`]}
          onNudge={(r) => handleAction(nudgeQuotation, r.quotation_id, "Nudge")}
          onEscalate={(r) => handleAction(escalateQuotation, r.quotation_id, "Escalation")}
          onOpen={(r) => navigate(`/app/quotations/${r.quotation_id}`)}
          busyId={busyId}
          emptyLabel="No stalled deals — pipeline is healthy."
        />
      </Panel>

      {/* ── Discount anomalies table ────────────────────────────────── */}
      <Panel
        title="Discount Anomalies"
        right={<span className="text-[11px] text-ink-muted flex items-center gap-1.5"><ShieldAlert className="h-3 w-3" /> Above rep z-score threshold</span>}
        noPad
      >
        <AlertTable
          rows={health?.discount_anomalies || []}
          columns={["Customer", "Current Discount", "Z-Score"]}
          renderRow={(r) => [r.customer_name, `${r.current_discount?.toFixed(1)}%`, r.z_score?.toFixed(2)]}
          onNudge={(r) => handleAction(nudgeQuotation, r.quotation_id, "Nudge")}
          onEscalate={(r) => handleAction(escalateQuotation, r.quotation_id, "Escalation")}
          onOpen={(r) => navigate(`/app/quotations/${r.quotation_id}`)}
          busyId={busyId}
          emptyLabel="No discount anomalies detected."
        />
      </Panel>

      {/* ── Delivery slippage table ─────────────────────────────────── */}
      <Panel
        title="Delivery Slippage"
        right={<span className="text-[11px] text-ink-muted flex items-center gap-1.5"><Truck className="h-3 w-3" /> Past expected delivery</span>}
        noPad
      >
        <AlertTable
          rows={health?.delivery_slippage || []}
          columns={["Customer", "Expected Delivery", "Days Late"]}
          renderRow={(r) => [r.customer_name, date(r.expected_delivery_date), `${r.days_late}d`]}
          onNudge={(r) => handleAction(nudgeQuotation, r.quotation_id, "Nudge")}
          onEscalate={(r) => handleAction(escalateQuotation, r.quotation_id, "Escalation")}
          onOpen={(r) => navigate(`/app/quotations/${r.quotation_id}`)}
          busyId={busyId}
          emptyLabel="No delivery slippage — all fulfilled on time."
        />
      </Panel>
    </section>
  );
}
