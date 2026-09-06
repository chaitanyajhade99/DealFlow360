import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, ShieldAlert, Truck, ArrowRight, Bell, TrendingUp } from "lucide-react";
import { getDealHealth, nudgeQuotation, escalateQuotation } from "../api/client";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, date } from "../utils";

export default function DealHealth() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const load = () => getDealHealth().then(setHealth);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const handleAction = async (fn, quotationId, label) => {
    setBusyId(quotationId);
    try {
      await fn(quotationId, {});
      toast(`${label} sent for ${code("Q", quotationId)}.`, "success");
    } catch (err) {
      toast(err.message || "Action failed.", "error");
    } finally {
      setBusyId(null);
    }
  };

  if (loading || !health) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton variant="card" />
          <Skeleton variant="card" />
          <Skeleton variant="card" />
        </div>
      </div>
    );
  }

  const cards = [
    { label: "Stalled Deals", value: health.stalled_deals.length, icon: Clock, borderClass: "border-amber-200/80", iconClass: "text-amber-500" },
    { label: "Discount Anomalies", value: health.discount_anomalies.length, icon: ShieldAlert, borderClass: "border-red-200/80", iconClass: "text-red-500" },
    { label: "Delivery Slippage", value: health.delivery_slippage.length, icon: Truck, borderClass: "border-sky-200/80", iconClass: "text-sky-500" },
  ];

  return (
    <section className="space-y-5 animate-fade-slide-in">
      <div>
        <h1 className="text-xl font-black tracking-tight text-slate-900 flex items-center gap-2">
          Deal Health & Anomaly Dashboard
          <span className="rounded-md bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700 border border-red-200">
            Live
          </span>
        </h1>
        <p className="mt-0.5 text-xs text-slate-500">
          Stalled quotes, discount anomalies (per-rep z-score), and delivery-promise slippage — click an alert to nudge or escalate.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {cards.map((c) => (
          <div key={c.label} className={`rounded-xl border ${c.borderClass} bg-white p-4 shadow-xs`}>
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider font-semibold text-slate-500">
              <c.icon className={`h-3.5 w-3.5 ${c.iconClass}`} />
              {c.label}
            </div>
            <div className="mt-2 text-3xl font-black text-slate-900 font-mono">{c.value}</div>
          </div>
        ))}
      </div>

      <Panel title="Stalled Deals" right={<span className="text-[11px] text-slate-400">Inactive 5+ days</span>}>
        <AlertTable
          rows={health.stalled_deals}
          columns={["Customer", "Status", "Days Inactive"]}
          renderRow={(r) => [r.customer_name, r.status.replaceAll("_", " "), r.days_inactive]}
          onNudge={(r) => handleAction(nudgeQuotation, r.quotation_id, "Nudge")}
          onEscalate={(r) => handleAction(escalateQuotation, r.quotation_id, "Escalation")}
          onOpen={(r) => navigate(`/app/quotations/${r.quotation_id}`)}
          busyId={busyId}
        />
      </Panel>

      <Panel title="Discount Anomalies" right={<span className="text-[11px] text-slate-400">Above rep's historical average</span>}>
        <AlertTable
          rows={health.discount_anomalies}
          columns={["Customer", "Current Discount", "Z-Score"]}
          renderRow={(r) => [r.customer_name, `${r.current_discount.toFixed(1)}%`, r.z_score.toFixed(2)]}
          onNudge={(r) => handleAction(nudgeQuotation, r.quotation_id, "Nudge")}
          onEscalate={(r) => handleAction(escalateQuotation, r.quotation_id, "Escalation")}
          onOpen={(r) => navigate(`/app/quotations/${r.quotation_id}`)}
          busyId={busyId}
        />
      </Panel>

      <Panel title="Delivery Slippage" right={<span className="text-[11px] text-slate-400">Past expected delivery, not yet delivered</span>}>
        <AlertTable
          rows={health.delivery_slippage}
          columns={["Customer", "Expected Delivery", "Days Late"]}
          renderRow={(r) => [r.customer_name, date(r.expected_delivery_date), r.days_late]}
          onNudge={(r) => handleAction(nudgeQuotation, r.quotation_id, "Nudge")}
          onEscalate={(r) => handleAction(escalateQuotation, r.quotation_id, "Escalation")}
          onOpen={(r) => navigate(`/app/quotations/${r.quotation_id}`)}
          busyId={busyId}
        />
      </Panel>
    </section>
  );
}

function AlertTable({ rows, columns, renderRow, onNudge, onEscalate, onOpen, busyId }) {
  if (!rows.length) {
    return <p className="text-xs text-slate-400 py-6 text-center">No alerts in this category right now.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="df-table">
        <thead>
          <tr>
            {columns.map((c) => <th key={c}>{c}</th>)}
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const cells = renderRow(r);
            const busy = busyId === r.quotation_id;
            return (
              <tr key={r.quotation_id}>
                {cells.map((c, i) => (
                  <td key={i} className={i === 0 ? "font-bold text-xs text-slate-900" : "text-xs text-slate-600 font-mono"}>{c}</td>
                ))}
                <td>
                  <div className="flex items-center gap-1.5">
                    <button onClick={() => onNudge(r)} disabled={busy} className="df-btn-secondary py-1 px-2 text-[11px] gap-1">
                      <Bell className="h-3 w-3" /> Nudge
                    </button>
                    <button onClick={() => onEscalate(r)} disabled={busy} className="df-btn-secondary py-1 px-2 text-[11px] gap-1 text-red-700 border-red-200">
                      <TrendingUp className="h-3 w-3" /> Escalate
                    </button>
                    <button onClick={() => onOpen(r)} className="df-btn-secondary py-1 px-2 text-[11px] gap-1">
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
