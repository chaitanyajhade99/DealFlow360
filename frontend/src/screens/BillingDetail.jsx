import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CreditCard, Repeat, FileMinus } from "lucide-react";
import { getSubscription, getSubscriptionCreditNotes, cancelSubscription, updateSubscription } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { date, money } from "../utils";

export default function BillingDetail() {
  const { id } = useParams();
  const { toast } = useToast();
  const [subscription, setSubscription] = useState(null);
  const [creditNotes, setCreditNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [newAmount, setNewAmount] = useState("");

  const load = () =>
    Promise.all([getSubscription(id), getSubscriptionCreditNotes(id)]).then(([sub, notes]) => {
      setSubscription(sub);
      setCreditNotes(notes);
      setNewAmount(sub.amount ?? "");
    });

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading || !subscription) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const handleModify = async () => {
    setBusy(true);
    try {
      const res = await updateSubscription(id, { amount: Number(newAmount) });
      setSubscription(res.subscription);
      if (res.proration_amount != null) {
        toast(
          res.proration_amount < 0
            ? `Prorated credit of ${money(Math.abs(res.proration_amount))} issued for the downgrade.`
            : `Prorated charge of ${money(res.proration_amount)} for the upgrade (raise manually via Invoices).`,
          "success"
        );
      }
      load();
    } catch (err) {
      toast(err.message || "Could not modify subscription.", "error");
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async () => {
    setBusy(true);
    try {
      const updated = await cancelSubscription(id, { reason: "Cancelled from billing detail" });
      setSubscription(updated);
      toast("Subscription cancelled — prorated refund credit note issued automatically.", "success");
      load();
    } catch (err) {
      toast(err.message || "Could not cancel subscription.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <DetailScreen
      title={`Billing Detail · ${subscription.customer_name}`}
      subtitle={`${subscription.plan} · ${subscription.cycle} · Status: ${subscription.status}`}
      actions={
        subscription.status === "cancelled"
          ? []
          : [
              { label: busy ? "Working..." : "Cancel Subscription", variant: "danger", onClick: handleCancel },
            ]
      }
      banner={{
        title: "Hybrid billing:",
        body: "Recurring lines bill on their own schedule, separate from one-time invoice lines. Modify/cancel compute real prorated amounts from days remaining in the current cycle.",
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
            <Repeat className="h-3.5 w-3.5 text-brand-600" /> Recurring Amount
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">
            {subscription.amount != null ? money(subscription.amount) : "—"}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {subscription.qty ? `${subscription.qty} seats · ` : ""}Next bill: {date(subscription.next_bill_date)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
            <CreditCard className="h-3.5 w-3.5 text-indigo-600" /> Status
          </div>
          <div className="mt-2"><StatusBadge value={subscription.status} /></div>
          {subscription.quotation_id && (
            <div className="text-[11px] text-slate-400 mt-1.5">Linked to quotation #{subscription.quotation_id}</div>
          )}
        </div>
      </div>

      {subscription.status !== "cancelled" && (
        <Panel title="Modify Subscription (Mid-Cycle Proration)">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="df-label">New Recurring Amount</label>
              <input
                type="number"
                step="0.01"
                className="df-input w-40 text-xs font-mono"
                value={newAmount}
                onChange={(e) => setNewAmount(e.target.value)}
              />
            </div>
            <button onClick={handleModify} disabled={busy} className="df-btn-primary text-xs">
              {busy ? "Working..." : "Apply Change"}
            </button>
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            Charge/credit is prorated by days remaining in the current billing cycle, not applied in full.
          </p>
        </Panel>
      )}

      <Panel
        title="Credit Notes"
        right={<span className="flex items-center gap-1 text-[11px] text-slate-500"><FileMinus className="h-3 w-3" /> {creditNotes.length} issued</span>}
      >
        {creditNotes.length ? (
          <div className="overflow-x-auto">
            <table className="df-table">
              <thead>
                <tr>
                  <th>Amount</th>
                  <th>Reason</th>
                  <th>Issued</th>
                </tr>
              </thead>
              <tbody>
                {creditNotes.map((c) => (
                  <tr key={c.id}>
                    <td className="font-mono text-xs font-bold text-slate-900">{money(c.amount)}</td>
                    <td className="text-xs text-slate-600">{c.reason || "—"}</td>
                    <td className="text-xs text-slate-400 font-mono">{date(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-slate-400 py-4 text-center">No credit notes issued for this subscription.</p>
        )}
      </Panel>
    </DetailScreen>
  );
}
