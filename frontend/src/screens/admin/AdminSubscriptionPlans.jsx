import { useEffect, useState } from "react";
import { Plus, Repeat, CheckCircle2, X } from "lucide-react";
import { getSubscriptionPlans, createSubscriptionPlan } from "../../api/client";
import AdminNav from "../../components/AdminNav";
import Panel from "../../components/Panel";
import Skeleton from "../../components/Skeleton";
import { useToast } from "../../context/ToastContext";

const emptyForm = { name: "", cycle: "Monthly", refund: "partial", notice_days: "30" };

export default function AdminSubscriptionPlans() {
  const { toast } = useToast();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState(emptyForm);

  const load = () => getSubscriptionPlans().then(setPlans);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast("Give the plan a name.", "warning");
      return;
    }
    setSaving(true);
    try {
      const created = await createSubscriptionPlan({
        name: formData.name,
        cycle: formData.cycle,
        proration_rule: { mid_cycle_qty_change: "prorate_remaining_days" },
        cancellation_rule: { refund: formData.refund, notice_days: Number(formData.notice_days) },
      });
      setPlans((prev) => [...prev, created]);
      setIsModalOpen(false);
      setFormData(emptyForm);
      toast(`Plan "${created.name}" created.`, "success");
    } catch (err) {
      toast(err.message || "Could not create plan.", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Skeleton variant="card" count={2} />;

  return (
    <div className="space-y-6 animate-fade-slide-in">
      <AdminNav />
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Subscription / Recurring Plan Setup</h1>
          <p className="mt-1 text-xs text-slate-500">PDF A5 — proration and cancellation rules for recurring plans.</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="df-btn-primary gap-1.5">
          <Plus className="h-4 w-4" /> New Plan
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {plans.map((p) => (
          <Panel key={p.id} title={p.name} right={<Repeat className="h-4 w-4 text-slate-400" />}>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Cycle</span><span className="font-bold">{p.cycle}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Refund on Cancel</span><span className="font-bold capitalize">{p.cancellation_rule?.refund || "—"}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Notice Days</span><span className="font-bold">{p.cancellation_rule?.notice_days ?? "—"}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Mid-Cycle Rule</span><span className="font-bold text-right">{p.proration_rule?.mid_cycle_qty_change?.replaceAll("_", " ") || "—"}</span></div>
            </div>
          </Panel>
        ))}
        {!plans.length && <p className="text-xs text-slate-400 col-span-full text-center py-8">No subscription plans configured yet.</p>}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h2 className="text-base font-bold text-slate-900">New Subscription Plan</h2>
              <button onClick={() => setIsModalOpen(false)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"><X className="h-4 w-4" /></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3.5">
              <div>
                <label className="df-label">Plan Name *</label>
                <input required className="df-input text-xs" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="e.g. Enterprise Support" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="df-label">Billing Cycle</label>
                  <select className="df-input text-xs" value={formData.cycle} onChange={(e) => setFormData({ ...formData, cycle: e.target.value })}>
                    <option value="Monthly">Monthly</option>
                    <option value="Quarterly">Quarterly</option>
                    <option value="Yearly">Yearly</option>
                  </select>
                </div>
                <div>
                  <label className="df-label">Cancellation Refund</label>
                  <select className="df-input text-xs" value={formData.refund} onChange={(e) => setFormData({ ...formData, refund: e.target.value })}>
                    <option value="partial">Partial (prorated)</option>
                    <option value="full">Full</option>
                    <option value="none">None</option>
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="df-label">Cancellation Notice (days)</label>
                  <input type="number" className="df-input text-xs font-mono" value={formData.notice_days} onChange={(e) => setFormData({ ...formData, notice_days: e.target.value })} />
                </div>
              </div>
              <div className="mt-5 flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button type="button" onClick={() => setIsModalOpen(false)} className="df-btn-secondary">Cancel</button>
                <button type="submit" disabled={saving} className="df-btn-primary gap-1.5"><CheckCircle2 className="h-3.5 w-3.5" />{saving ? "Saving..." : "Create"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
