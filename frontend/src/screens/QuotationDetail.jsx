import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Sparkles,
  Plus,
  Check,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Building2,
  TrendingUp,
} from "lucide-react";
import { getQuotationDetail, saveQuotationLineDiscount } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { code, lineTotal, money, pct } from "../utils";

export default function QuotationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState({ quotation: null, lines: [] });
  const [discounts, setDiscounts] = useState({});
  const [addedUpsells, setAddedUpsells] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getQuotationDetail(id).then((d) => {
      setData(d);
      setDiscounts(Object.fromEntries(d.lines.map((l) => [l.id, l.discount_pct])));
      setLoading(false);
    });
  }, [id]);

  const lines = data.lines;
  const triggers = useMemo(
    () =>
      lines.filter(
        (l) => Number(discounts[l.id] ?? l.discount_pct) > Number(l.category_limit_pct)
      ),
    [lines, discounts]
  );

  const blendedRisk = triggers.length
    ? "HIGH"
    : lines.some(
        (l) => Number(discounts[l.id] ?? l.discount_pct) > Number(l.category_limit_pct) * 0.8
      )
    ? "MEDIUM"
    : "LOW";

  const total = lines.reduce(
    (sum, line) => sum + lineTotal(line, discounts[line.id] ?? line.discount_pct),
    0
  );

  if (loading || !data.quotation) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const updateDiscount = (line, value) => {
    const next = value === "" ? "" : Number(value);
    setDiscounts((prev) => ({ ...prev, [line.id]: next }));
    saveQuotationLineDiscount(line.id, next);
  };

  const handleToggleUpsell = (key) => {
    setAddedUpsells((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <DetailScreen
      title={`Quotation Detail · ${code("Q", data.quotation.id)}`}
      subtitle={`${data.quotation.customer_name} · ${data.quotation.customer_tier} Tier · Status: ${data.quotation.status.replaceAll("_", " ")}`}
      actions={[
        { label: "Save Draft", onClick: () => {} },
        {
          label: "Send for Approval",
          primary: true,
          onClick: () => navigate(`/app/approvals/${data.quotation.id === 1042 ? 501 : 500}`),
        },
      ]}
      banner={
        triggers.length
          ? {
              tone: "danger",
              title: "High blended risk triggered:",
              body: `Breached category limits on: ${triggers
                .map(
                  (l) =>
                    `${l.product_id} (${pct(discounts[l.id])} requested vs ${pct(l.category_limit_pct)} limit)`
                )
                .join("; ")}. Requires Sales Manager + Finance approval chain.`,
            }
          : {
              title: `Blended risk: ${blendedRisk}.`,
              body: "All line discounts are currently within snapshotted category limits.",
            }
      }
      sidePanel={
        <Panel
          title="Upsell & Cross-Sell Suggestions"
          right={
            <span className="flex items-center gap-1 text-[11px] font-bold text-brand-600 bg-brand-50 px-2 py-0.5 rounded border border-brand-200/50">
              <Sparkles className="h-3 w-3" /> AI Engine
            </span>
          }
        >
          <div className="space-y-3">
            {/* Upsell Card 1 */}
            <div className="group rounded-xl border border-slate-200/90 bg-white p-3.5 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-bold text-slate-800">USB-C Pro Dock</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Recommended with Laptop Pro 14</div>
                </div>
                <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                  +24% Margin
                </span>
              </div>
              <div className="mt-2.5 flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                <span className="font-mono font-bold text-slate-700">$160.00 / ea</span>
                <button
                  onClick={() => handleToggleUpsell("dock")}
                  className={`df-btn text-xs py-1 px-2.5 ${
                    addedUpsells["dock"] ? "df-btn-success" : "df-btn-secondary"
                  }`}
                  aria-label="Add USB-C Dock to quote"
                >
                  {addedUpsells["dock"] ? (
                    <>
                      <Check className="h-3 w-3" /> Added
                    </>
                  ) : (
                    <>
                      <Plus className="h-3 w-3" /> Add Item
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Upsell Card 2 */}
            <div className="group rounded-xl border border-slate-200/90 bg-white p-3.5 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-bold text-slate-800">Care Plan 2yr Support</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Recurring SLA coverage tier</div>
                </div>
                <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                  +18% Margin
                </span>
              </div>
              <div className="mt-2.5 flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                <span className="font-mono font-bold text-slate-700">$240.00 / yr</span>
                <button
                  onClick={() => handleToggleUpsell("care")}
                  className={`df-btn text-xs py-1 px-2.5 ${
                    addedUpsells["care"] ? "df-btn-success" : "df-btn-secondary"
                  }`}
                  aria-label="Add Care Plan 2yr to quote"
                >
                  {addedUpsells["care"] ? (
                    <>
                      <Check className="h-3 w-3" /> Added
                    </>
                  ) : (
                    <>
                      <Plus className="h-3 w-3" /> Add Item
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </Panel>
      }
    >
      {/* Line Items Table Panel */}
      <Panel
        title="Commercial Line Items & Discount Guardrails"
        right={
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Total:</span>
            <span className="font-mono text-sm font-black text-slate-900">{money(total)}</span>
          </div>
        }
      >
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Product Code</th>
                <th>Category</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Discount %</th>
                <th>Category Limit</th>
                <th>Status</th>
                <th>Line Total</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, idx) => {
                const d = discounts[line.id] ?? line.discount_pct;
                const isOver = d !== "" && Number(d) > Number(line.category_limit_pct);
                const isNear =
                  !isOver &&
                  d !== "" &&
                  Number(d) > Number(line.category_limit_pct) * 0.8;

                return (
                  <tr
                    key={line.id}
                    className={`transition-colors animate-stagger-${idx + 1}`}
                  >
                    <td>
                      <div className="font-mono text-xs font-bold text-slate-900">{line.product_id}</div>
                      <div className="text-[11px] text-slate-400">Line #{line.id}</div>
                    </td>
                    <td>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                        {line.category}
                      </span>
                    </td>
                    <td className="font-semibold text-slate-700">{line.qty}</td>
                    <td className="font-mono text-xs text-slate-700">{money(line.unit_price)}</td>
                    <td>
                      <div className="relative w-28">
                        <input
                          aria-label={`Discount percentage for ${line.product_id}`}
                          className={`w-full rounded-md border px-2.5 py-1 text-xs font-mono font-bold transition-all duration-200 outline-none ${
                            isOver
                              ? "border-red-400 bg-red-50/80 text-red-900 ring-2 ring-red-200 animate-pulse-scale"
                              : isNear
                              ? "border-amber-400 bg-amber-50/80 text-amber-900"
                              : "border-slate-300 bg-white text-slate-900 focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                          }`}
                          type="number"
                          min="0"
                          max="100"
                          step="0.5"
                          value={d}
                          onChange={(e) => updateDiscount(line, e.target.value)}
                        />
                        <span className="absolute right-2 top-1.5 text-xs text-slate-400 font-mono pointer-events-none">
                          %
                        </span>
                      </div>
                    </td>
                    <td className="font-mono text-xs font-semibold text-slate-600">
                      {pct(line.category_limit_pct)}
                    </td>
                    <td>
                      {/* Animated Status Pill */}
                      <span
                        key={isOver ? "over" : "ok"}
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold tracking-tight transition-all duration-300 ${
                          isOver
                            ? "bg-red-100 text-red-800 border border-red-200 animate-pulse-scale"
                            : isNear
                            ? "bg-amber-100 text-amber-800 border border-amber-200"
                            : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                        }`}
                      >
                        {isOver ? (
                          <>
                            <ShieldAlert className="h-3 w-3 text-red-600" />
                            <span>OVER LIMIT</span>
                          </>
                        ) : (
                          <>
                            <ShieldCheck className="h-3 w-3 text-emerald-600" />
                            <span>OK</span>
                          </>
                        )}
                      </span>
                    </td>
                    <td
                      className={`font-mono text-xs font-bold ${
                        isOver ? "text-red-700" : "text-slate-900"
                      }`}
                    >
                      {money(lineTotal(line, d || 0))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Quote Summary Overview */}
      <Panel title="Commercial Summary & Risk Matrix">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="df-label">Customer Account</div>
            <div className="text-sm font-bold text-slate-900 mt-0.5">{data.quotation.customer_name}</div>
            <div className="text-[11px] text-slate-400">Account #{data.quotation.id}</div>
          </div>
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="df-label">Customer Tier</div>
            <div className="mt-0.5 flex items-center gap-1.5">
              <StatusBadge value={data.quotation.customer_tier === "Gold" ? "approved" : "draft"} />
              <span className="text-xs font-bold text-slate-800">{data.quotation.customer_tier}</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">Tier discounts eligible</div>
          </div>
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="df-label">Blended Risk Assessment</div>
            <div className="mt-0.5">
              <StatusBadge value={blendedRisk} />
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {blendedRisk === "HIGH" ? "Multi-level signoff" : "Standard path"}
            </div>
          </div>
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="df-label">Net Commercial Total</div>
            <div className="font-mono text-base font-extrabold text-slate-900 mt-0.5">{money(total)}</div>
            <div className="text-[11px] text-slate-400">Taxes computed at billing</div>
          </div>
        </div>
      </Panel>
    </DetailScreen>
  );
}

