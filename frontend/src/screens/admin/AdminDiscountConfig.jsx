import { useEffect, useState } from "react";
import { Save, CheckCircle2, Info, Plus } from "lucide-react";
import { getDiscountTiers, updateDiscountTier, createDiscountTier } from "../../api/client";
import AdminNav from "../../components/AdminNav";
import Panel from "../../components/Panel";
import Skeleton from "../../components/Skeleton";
import { useToast } from "../../context/ToastContext";

const CATEGORIES = ["Hardware", "Services", "Subscription"];
const emptyTier = { name: "", max_discount_pct: 5, category_limits: { Hardware: 5, Services: 3, Subscription: 5 }, approval_chain: { LOW: "none", MEDIUM: "sales_manager", HIGH: "sales_manager_then_finance" } };

export default function AdminDiscountConfig() {
  const { toast } = useToast();
  const [tiers, setTiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [newTier, setNewTier] = useState(null);

  const load = () => getDiscountTiers().then(setTiers);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const handleTierChange = (tierId, field, value) => {
    setTiers((prev) => prev.map((t) => (t.id === tierId ? { ...t, [field]: Number(value) } : t)));
  };
  const handleCategoryLimitChange = (tierId, cat, value) => {
    setTiers((prev) => prev.map((t) => (t.id === tierId ? { ...t, category_limits: { ...t.category_limits, [cat]: Number(value) } } : t)));
  };

  const handleSave = async (tier) => {
    setSavingId(tier.id);
    try {
      await updateDiscountTier(tier.id, {
        name: tier.name,
        max_discount_pct: tier.max_discount_pct,
        category_limits: tier.category_limits,
        approval_chain: tier.approval_chain,
      });
      toast(`${tier.name} tier saved.`, "success");
    } catch (err) {
      toast(err.message || "Could not save tier.", "error");
    } finally {
      setSavingId(null);
    }
  };

  const handleCreateTier = async () => {
    if (!newTier.name.trim()) {
      toast("Give the new tier a name.", "warning");
      return;
    }
    try {
      const created = await createDiscountTier(newTier);
      setTiers((prev) => [...prev, created]);
      setNewTier(null);
      toast(`${created.name} tier created.`, "success");
    } catch (err) {
      toast(err.message || "Could not create tier.", "error");
    }
  };

  if (loading) return <Skeleton variant="card" count={3} />;

  return (
    <div className="space-y-6 animate-fade-slide-in">
      <AdminNav />
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Discount Tiers & Approval Chain Governance</h1>
          <p className="mt-1 text-xs text-slate-500">PDF A3 — real tier ceilings, category limits, and approval routing.</p>
        </div>
        <button onClick={() => setNewTier(emptyTier)} className="df-btn-secondary gap-1.5 self-start sm:self-auto">
          <Plus className="h-4 w-4" /> New Tier
        </button>
      </div>

      <div className="flex items-start gap-3 rounded-lg border border-indigo-200 bg-indigo-50/70 p-4 text-xs text-indigo-950">
        <Info className="h-4 w-4 text-indigo-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">How Guardrails Work:</span> When reps build quotations, any discount exceeding
          the tier max or category ceiling flags the line and routes to the required approval chain
          (Sales Manager, or Sales Manager followed by Finance for HIGH risk).
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {tiers.map((tier) => (
          <div key={tier.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-black text-slate-800">{tier.name} Tier</span>
              <span className="text-[11px] font-mono text-slate-400">Tier #{tier.id}</span>
            </div>
            <div className="space-y-4">
              <div>
                <label className="df-label">Overall Max Discount Ceiling (%)</label>
                <input type="number" min="0" max="50" className="df-input font-mono font-bold text-sm" value={tier.max_discount_pct} onChange={(e) => handleTierChange(tier.id, "max_discount_pct", e.target.value)} />
              </div>
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Category Discount Limits</div>
                <div className="grid grid-cols-3 gap-2">
                  {CATEGORIES.map((cat) => (
                    <div key={cat}>
                      <span className="block text-[10px] font-medium text-slate-600 mb-1">{cat}</span>
                      <input type="number" min="0" max="40" className="df-input text-xs font-mono" value={tier.category_limits?.[cat] || 0} onChange={(e) => handleCategoryLimitChange(tier.id, cat, e.target.value)} />
                    </div>
                  ))}
                </div>
              </div>
              <button onClick={() => handleSave(tier)} disabled={savingId === tier.id} className="df-btn-primary w-full gap-1.5 text-xs">
                <Save className="h-3.5 w-3.5" />
                {savingId === tier.id ? "Saving..." : "Save Tier"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {newTier && (
        <Panel title="New Discount Tier">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="df-label">Tier Name</label>
              <input className="df-input text-xs" value={newTier.name} onChange={(e) => setNewTier({ ...newTier, name: e.target.value })} placeholder="e.g. Platinum" />
            </div>
            <div>
              <label className="df-label">Max Discount %</label>
              <input type="number" className="df-input text-xs" value={newTier.max_discount_pct} onChange={(e) => setNewTier({ ...newTier, max_discount_pct: Number(e.target.value) })} />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button onClick={() => setNewTier(null)} className="df-btn-secondary text-xs">Cancel</button>
            <button onClick={handleCreateTier} className="df-btn-primary gap-1.5 text-xs">
              <CheckCircle2 className="h-4 w-4" /> Create Tier
            </button>
          </div>
        </Panel>
      )}
    </div>
  );
}
