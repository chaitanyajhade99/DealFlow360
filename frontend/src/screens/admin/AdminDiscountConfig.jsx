import { useState } from "react";
import {
  ShieldAlert,
  Save,
  CheckCircle2,
  Sliders,
  Sparkles,
  Layers,
  ArrowRight,
  Info,
  HelpCircle,
} from "lucide-react";
import { discount_tiers as initialTiers } from "../../api/mockData";
import Panel from "../../components/Panel";
import { useToast } from "../../context/ToastContext";
import { pct } from "../../utils";

export default function AdminDiscountConfig() {
  const { toast } = useToast();
  const [tiers, setTiers] = useState(initialTiers);
  const [savedAt, setSavedAt] = useState(null);

  // Global policy parameters
  const [globalLimits, setGlobalLimits] = useState({
    autoApproveUnderPct: 5,
    managerThresholdPct: 15,
    financeEscalationPct: 20,
    allowNegativeMarginOverride: false,
  });

  const handleTierChange = (tierId, field, value) => {
    setTiers((prev) =>
      prev.map((t) => (t.id === tierId ? { ...t, [field]: Number(value) } : t))
    );
  };

  const handleCategoryLimitChange = (tierId, cat, value) => {
    setTiers((prev) =>
      prev.map((t) =>
        t.id === tierId
          ? {
              ...t,
              category_limits: {
                ...t.category_limits,
                [cat]: Number(value),
              },
            }
          : t
      )
    );
  };

  const handleSave = (e) => {
    e.preventDefault();
    setSavedAt(new Date().toLocaleTimeString());
    toast("Discount governance policies & approval chains saved successfully.", "success");
  };

  return (
    <div className="space-y-6 animate-fade-slide-in">
      {/* Header */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Discount Tiers & Approval Chain Governance
            </h1>
            <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-[10px] font-bold text-purple-800 border border-purple-200">
              Admin Exclusive
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Define automated discount ceilings, category variances, and multi-tier routing policies.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="df-btn-primary gap-1.5 shadow-sm self-start sm:self-auto"
          aria-label="Save discount policy configuration"
        >
          <Save className="h-4 w-4" />
          <span>Save Configuration</span>
        </button>
      </div>

      {savedAt && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs text-emerald-900 animate-fade-slide-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>
              Configuration active and applied in-memory at <b>{savedAt}</b>. Quotation builder will enforce these rules.
            </span>
          </div>
        </div>
      )}

      {/* Explanatory Banner */}
      <div className="flex items-start gap-3 rounded-lg border border-indigo-200 bg-indigo-50/70 p-4 text-xs text-indigo-950">
        <Info className="h-4 w-4 text-indigo-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">How Guardrails Work:</span> When sales representatives construct quotations, any discount percentage exceeding the tier max or category ceiling automatically flags the line item and routes the deal to the required approval chain (Sales Manager followed by Finance).
        </div>
      </div>

      {/* Tiers Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {tiers.map((tier) => {
          const isGold = tier.name.toLowerCase() === "gold";
          const isSilver = tier.name.toLowerCase() === "silver";

          let borderAccent = "border-amber-300";
          let badgeBg = "bg-amber-100 text-amber-900";
          if (isSilver) {
            borderAccent = "border-slate-300";
            badgeBg = "bg-slate-200 text-slate-800";
          } else if (isGold) {
            borderAccent = "border-yellow-400";
            badgeBg = "bg-yellow-100 text-yellow-900";
          }

          return (
            <div
              key={tier.id}
              className={`rounded-xl border ${borderAccent} bg-white p-5 shadow-xs transition-all hover:shadow-md`}
            >
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-black ${badgeBg}`}>
                    {tier.name} Tier
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">Tier #{tier.id}</span>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="df-label">Overall Max Discount Ceiling (%)</label>
                  <div className="relative">
                    <input
                      type="number"
                      min="0"
                      max="50"
                      className="df-input font-mono font-bold text-sm"
                      value={tier.max_discount_pct}
                      onChange={(e) => handleTierChange(tier.id, "max_discount_pct", e.target.value)}
                    />
                    <span className="absolute right-3 top-2.5 text-xs font-bold text-slate-400">%</span>
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Category Discount Limits
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <span className="block text-[10px] font-medium text-slate-600 mb-1">Hardware</span>
                      <input
                        type="number"
                        min="0"
                        max="40"
                        className="df-input text-xs font-mono"
                        value={tier.category_limits?.Hardware || 0}
                        onChange={(e) =>
                          handleCategoryLimitChange(tier.id, "Hardware", e.target.value)
                        }
                      />
                    </div>
                    <div>
                      <span className="block text-[10px] font-medium text-slate-600 mb-1">Services</span>
                      <input
                        type="number"
                        min="0"
                        max="40"
                        className="df-input text-xs font-mono"
                        value={tier.category_limits?.Services || 0}
                        onChange={(e) =>
                          handleCategoryLimitChange(tier.id, "Services", e.target.value)
                        }
                      />
                    </div>
                    <div>
                      <span className="block text-[10px] font-medium text-slate-600 mb-1">Subscription</span>
                      <input
                        type="number"
                        min="0"
                        max="40"
                        className="df-input text-xs font-mono"
                        value={tier.category_limits?.Subscription || 0}
                        onChange={(e) =>
                          handleCategoryLimitChange(tier.id, "Subscription", e.target.value)
                        }
                      />
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 space-y-1.5 text-xs">
                  <div className="text-[11px] font-bold text-slate-700">Approval Routing Trigger</div>
                  <div className="rounded-lg bg-slate-50 p-2 text-[11px] text-slate-600 space-y-1">
                    <div className="flex justify-between">
                      <span className="font-medium text-slate-500">Low Risk:</span>
                      <span className="font-semibold text-emerald-700">Auto-Pass</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-medium text-slate-500">Medium Risk:</span>
                      <span className="font-semibold text-indigo-700">Sales Manager</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-medium text-slate-500">High Risk:</span>
                      <span className="font-semibold text-purple-700">Manager + Finance</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Global Risk Thresholds */}
      <Panel title="Global Governance Thresholds & Multi-Step Routing Matrix">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-4">
            <label className="df-label">Auto-Approval Threshold</label>
            <div className="text-xs text-slate-500 mb-2">
              Quotes with overall discount below this rate bypass manual approval entirely.
            </div>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="10"
                className="df-input font-mono text-xs"
                value={globalLimits.autoApproveUnderPct}
                onChange={(e) =>
                  setGlobalLimits({ ...globalLimits, autoApproveUnderPct: Number(e.target.value) })
                }
              />
              <span className="absolute right-3 top-2 text-xs font-bold text-slate-400">%</span>
            </div>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-4">
            <label className="df-label">Sales Manager Ceiling</label>
            <div className="text-xs text-slate-500 mb-2">
              Maximum discount percentage a Sales Manager can approve solo.
            </div>
            <div className="relative">
              <input
                type="number"
                min="5"
                max="25"
                className="df-input font-mono text-xs"
                value={globalLimits.managerThresholdPct}
                onChange={(e) =>
                  setGlobalLimits({ ...globalLimits, managerThresholdPct: Number(e.target.value) })
                }
              />
              <span className="absolute right-3 top-2 text-xs font-bold text-slate-400">%</span>
            </div>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-4">
            <label className="df-label">Finance Escalation Trigger</label>
            <div className="text-xs text-slate-500 mb-2">
              Any discount exceeding this rate mandates dual Signoff from VP Finance.
            </div>
            <div className="relative">
              <input
                type="number"
                min="10"
                max="40"
                className="df-input font-mono text-xs"
                value={globalLimits.financeEscalationPct}
                onChange={(e) =>
                  setGlobalLimits({ ...globalLimits, financeEscalationPct: Number(e.target.value) })
                }
              />
              <span className="absolute right-3 top-2 text-xs font-bold text-slate-400">%</span>
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button onClick={handleSave} className="df-btn-primary gap-1.5" aria-label="Save all changes">
            <CheckCircle2 className="h-4 w-4" />
            <span>Apply Governance Rules</span>
          </button>
        </div>
      </Panel>
    </div>
  );
}
