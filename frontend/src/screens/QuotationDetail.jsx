import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Sparkles, Plus, Trash2, ShieldAlert, ShieldCheck, TrendingUp } from "lucide-react";
import {
  getQuotationDetail,
  updateQuotationLines,
  submitQuotation,
  createQuotation,
  getUpsellSuggestions,
  getProducts,
  downloadQuotationPdf,
} from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, lineTotal, money, pct } from "../utils";

const CATEGORIES = ["Hardware", "Services", "Subscription"];
const TIERS = ["Bronze", "Silver", "Gold"];

function emptyLine() {
  return { product_id: "", category: "Hardware", qty: 1, unit_price: 0, discount_pct: 0 };
}

export default function QuotationDetail() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const { toast } = useToast();

  const [data, setData] = useState({ quotation: null, lines: [] });
  const [products, setProducts] = useState([]);
  const [lines, setLines] = useState(isNew ? [emptyLine()] : []);
  const [customerName, setCustomerName] = useState("");
  const [customerTier, setCustomerTier] = useState("Gold");
  const [upsell, setUpsell] = useState([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      await downloadQuotationPdf(id);
    } catch (err) {
      toast(err.message || "Could not generate PDF.", "error");
    } finally {
      setDownloadingPdf(false);
    }
  };

  useEffect(() => {
    getProducts().then(setProducts).catch(() => setProducts([]));
    if (isNew) return;
    getQuotationDetail(id).then((d) => {
      setData(d);
      setLines(d.lines.map((l) => ({ ...l })));
      setLoading(false);
      getUpsellSuggestions(id).then(setUpsell).catch(() => setUpsell([]));
    });
  }, [id, isNew]);

  const triggers = useMemo(
    () => lines.filter((l) => l.category_limit_pct != null && Number(l.discount_pct) > Number(l.category_limit_pct)),
    [lines]
  );
  const blendedRisk = triggers.length
    ? "HIGH"
    : lines.some((l) => l.category_limit_pct != null && Number(l.discount_pct) > Number(l.category_limit_pct) * 0.8)
    ? "MEDIUM"
    : "LOW";
  const total = lines.reduce((sum, line) => sum + lineTotal(line), 0);

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const quotation = data.quotation;
  const readOnly = !isNew && quotation && !["draft", "negotiation"].includes(quotation.status);

  const updateLine = (idx, field, value) => {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  };
  const addLine = () => setLines((prev) => [...prev, emptyLine()]);
  const removeLine = (idx) => setLines((prev) => prev.filter((_, i) => i !== idx));

  const handleSaveNew = async () => {
    if (!customerName.trim()) {
      toast("Enter a customer name first.", "warning");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        customer_name: customerName,
        customer_tier: customerTier,
        lines: lines
          .filter((l) => l.product_id)
          .map((l) => ({
            product_id: l.product_id,
            category: l.category,
            qty: Number(l.qty),
            unit_price: Number(l.unit_price),
            discount_pct: Number(l.discount_pct || 0),
          })),
      };
      const created = await createQuotation(payload);
      toast(`Quotation ${code("Q", created.id)} created.`, "success");
      navigate(`/app/quotations/${created.id}`);
    } catch (err) {
      toast(err.message || "Could not create quotation.", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveLines = async () => {
    setSaving(true);
    try {
      const payload = {
        lines: lines.map((l) => ({
          product_id: l.product_id,
          category: l.category,
          qty: Number(l.qty),
          unit_price: Number(l.unit_price),
          discount_pct: Number(l.discount_pct || 0),
        })),
        reason: "Edited from quotation builder",
      };
      const updated = await updateQuotationLines(id, payload);
      setData({ quotation: updated, lines: updated.lines });
      setLines(updated.lines.map((l) => ({ ...l })));
      toast("Line changes saved.", "success");
    } catch (err) {
      toast(err.message || "Could not save changes.", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      await handleSaveLines();
      const approval = await submitQuotation(id);
      toast(
        approval.stage === "confirmed"
          ? "No approval required — quotation confirmed."
          : `Routed for approval: ${approval.stage.replace("_", " ")} (${approval.blended_risk} risk).`,
        "success"
      );
      navigate(approval.stage === "confirmed" ? `/app/quotations/${id}` : `/app/approvals/${approval.id}`);
    } catch (err) {
      toast(err.message || "Could not submit quotation.", "error");
    } finally {
      setSaving(false);
    }
  };

  if (isNew) {
    return (
      <DetailScreen
        title="New Quotation"
        subtitle="Build a quotation, then submit for automatic approval routing."
        actions={[
          {
            label: saving ? "Saving..." : "Create Quotation",
            primary: true,
            onClick: handleSaveNew,
          },
        ]}
      >
        <Panel title="Customer">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="df-label">Customer Name</label>
              <input
                className="df-input text-xs"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="e.g. Acme Corp"
              />
            </div>
            <div>
              <label className="df-label">Customer Tier</label>
              <select className="df-input text-xs" value={customerTier} onChange={(e) => setCustomerTier(e.target.value)}>
                {TIERS.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>
        </Panel>

        <LineEditor lines={lines} products={products} onUpdate={updateLine} onAdd={addLine} onRemove={removeLine} />
      </DetailScreen>
    );
  }

  return (
    <DetailScreen
      title={`Quotation Detail · ${code("Q", quotation.id)}`}
      subtitle={`${quotation.customer_name} · ${quotation.customer_tier} Tier · Status: ${quotation.status.replaceAll("_", " ")}`}
      actions={[
        { label: downloadingPdf ? "Generating..." : "Download PDF", onClick: handleDownloadPdf },
        ...(readOnly
          ? []
          : [
              { label: saving ? "Saving..." : "Save Changes", onClick: handleSaveLines },
              { label: "Submit for Approval", primary: true, onClick: handleSubmit },
            ]),
      ]}
      banner={
        triggers.length
          ? {
              tone: "danger",
              title: "High blended risk:",
              body: `Breached category limits on: ${triggers
                .map((l) => `${l.product_id} (${pct(l.discount_pct)} vs ${pct(l.category_limit_pct)} limit)`)
                .join("; ")}. Will require Sales Manager + Finance approval.`,
            }
          : {
              title: `Blended risk: ${blendedRisk}.`,
              body: readOnly
                ? "This quotation is no longer editable in its current status."
                : "All line discounts are currently within category limits.",
            }
      }
      sidePanel={
        <Panel
          title="Upsell & Cross-Sell Suggestions"
          right={
            <span className="flex items-center gap-1 text-[11px] font-bold text-brand-600 bg-brand-50 px-2 py-0.5 rounded border border-brand-200/50">
              <Sparkles className="h-3 w-3" /> Live Engine
            </span>
          }
        >
          {upsell.length ? (
            <div className="space-y-3">
              {upsell.map((s) => (
                <div key={s.product_id} className="rounded-xl border border-slate-200/90 bg-white p-3.5 shadow-xs">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-xs font-bold text-slate-800">{s.product_name}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{s.promo_tag || "Recommended pairing"}</div>
                    </div>
                    <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                      +{money(s.margin_delta)} margin
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No upsell suggestions for the current cart.</p>
          )}
        </Panel>
      }
    >
      <Panel
        title="Commercial Line Items & Discount Guardrails"
        right={
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Total:</span>
            <span className="font-mono text-sm font-black text-slate-900">{money(total)}</span>
            {quotation.total_margin != null && (
              <span className="ml-2 flex items-center gap-1 text-[11px] font-bold text-emerald-700">
                <TrendingUp className="h-3 w-3" /> {money(quotation.total_margin)} margin
              </span>
            )}
          </div>
        }
      >
        <LineEditor
          lines={lines}
          products={products}
          onUpdate={updateLine}
          onAdd={addLine}
          onRemove={removeLine}
          readOnly={readOnly}
        />
      </Panel>
    </DetailScreen>
  );
}

function LineEditor({ lines, products, onUpdate, onAdd, onRemove, readOnly }) {
  return (
    <div className="overflow-x-auto">
      <table className="df-table">
        <thead>
          <tr>
            <th>Product</th>
            <th>Category</th>
            <th>Qty</th>
            <th>Unit Price</th>
            <th>Discount %</th>
            <th>Category Limit</th>
            <th>Status</th>
            <th>Line Total</th>
            {!readOnly && <th></th>}
          </tr>
        </thead>
        <tbody>
          {lines.map((line, idx) => {
            const d = line.discount_pct;
            const limit = line.category_limit_pct;
            const isOver = limit != null && Number(d) > Number(limit);
            const isNear = !isOver && limit != null && Number(d) > Number(limit) * 0.8;
            return (
              <tr key={idx}>
                <td>
                  {readOnly ? (
                    <div className="font-mono text-xs font-bold text-slate-900">{line.product_name || line.product_id}</div>
                  ) : (
                    <select
                      className="df-input text-xs py-1"
                      value={line.product_id}
                      onChange={(e) => {
                        const p = products.find((x) => x.product_code === e.target.value);
                        onUpdate(idx, "product_id", e.target.value);
                        if (p) {
                          onUpdate(idx, "category", p.category);
                          onUpdate(idx, "unit_price", p.price);
                        }
                      }}
                    >
                      <option value="">Select product…</option>
                      {products.map((p) => (
                        <option key={p.product_code} value={p.product_code}>{p.name} ({p.product_code})</option>
                      ))}
                    </select>
                  )}
                </td>
                <td>
                  {readOnly ? (
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">{line.category}</span>
                  ) : (
                    <select className="df-input text-xs py-1" value={line.category} onChange={(e) => onUpdate(idx, "category", e.target.value)}>
                      {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  )}
                </td>
                <td>
                  {readOnly ? <span className="font-semibold text-slate-700">{line.qty}</span> : (
                    <input type="number" min="1" className="df-input w-16 text-xs py-1" value={line.qty} onChange={(e) => onUpdate(idx, "qty", e.target.value)} />
                  )}
                </td>
                <td>
                  {readOnly ? <span className="font-mono text-xs text-slate-700">{money(line.unit_price)}</span> : (
                    <input type="number" min="0" step="0.01" className="df-input w-24 text-xs py-1" value={line.unit_price} onChange={(e) => onUpdate(idx, "unit_price", e.target.value)} />
                  )}
                </td>
                <td>
                  <div className="relative w-28">
                    <input
                      aria-label={`Discount percentage for line ${idx + 1}`}
                      disabled={readOnly}
                      className={`w-full rounded-md border px-2.5 py-1 text-xs font-mono font-bold transition-all duration-200 outline-none ${
                        isOver
                          ? "border-red-400 bg-red-50/80 text-red-900 ring-2 ring-red-200"
                          : isNear
                          ? "border-amber-400 bg-amber-50/80 text-amber-900"
                          : "border-slate-300 bg-white text-slate-900 focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                      }`}
                      type="number"
                      min="0"
                      max="100"
                      step="0.5"
                      value={d}
                      onChange={(e) => onUpdate(idx, "discount_pct", e.target.value)}
                    />
                    <span className="absolute right-2 top-1.5 text-xs text-slate-400 font-mono pointer-events-none">%</span>
                  </div>
                </td>
                <td className="font-mono text-xs font-semibold text-slate-600">{limit != null ? pct(limit) : "auto"}</td>
                <td>
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                    isOver ? "bg-red-100 text-red-800 border border-red-200" : isNear ? "bg-amber-100 text-amber-800 border border-amber-200" : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                  }`}>
                    {isOver ? <><ShieldAlert className="h-3 w-3" /> OVER LIMIT</> : <><ShieldCheck className="h-3 w-3" /> OK</>}
                  </span>
                </td>
                <td className={`font-mono text-xs font-bold ${isOver ? "text-red-700" : "text-slate-900"}`}>{money(lineTotal(line))}</td>
                {!readOnly && (
                  <td>
                    <button onClick={() => onRemove(idx)} className="text-slate-400 hover:text-red-600" aria-label="Remove line">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
      {!readOnly && (
        <button onClick={onAdd} className="df-btn-secondary mt-3 text-xs gap-1.5">
          <Plus className="h-3.5 w-3.5" /> Add Line
        </button>
      )}
    </div>
  );
}
