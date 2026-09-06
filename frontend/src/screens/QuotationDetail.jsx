import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Sparkles, Plus, Trash2, ShieldAlert, ShieldCheck, TrendingUp, X, UserPlus } from "lucide-react";
import {
  getQuotationDetail,
  updateQuotationLines,
  submitQuotation,
  createQuotation,
  getUpsellSuggestions,
  getProducts,
  downloadQuotationPdf,
  getCustomers,
  createCustomer,
  getQuotationNegotiations,
  respondToNegotiation,
} from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, lineTotal, money, pct } from "../utils";

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
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [newCustomerOpen, setNewCustomerOpen] = useState(false);
  const [newCustomerName, setNewCustomerName] = useState("");
  const [addingCustomer, setAddingCustomer] = useState(false);
  const [upsell, setUpsell] = useState([]);
  const [negotiations, setNegotiations] = useState([]);
  const [respondingId, setRespondingId] = useState(null);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const selectedCustomer = customers.find((c) => String(c.id) === String(selectedCustomerId));

  const loadCustomers = () => getCustomers().then(setCustomers).catch(() => setCustomers([]));

  const handleAddCustomer = async (e) => {
    e.preventDefault();
    if (!newCustomerName.trim()) {
      toast("Enter a company name.", "warning");
      return;
    }
    setAddingCustomer(true);
    try {
      const created = await createCustomer({ name: newCustomerName.trim() });
      toast(`${created.name} added — starts at Bronze tier.`, "success");
      setCustomers((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedCustomerId(String(created.id));
      setNewCustomerOpen(false);
      setNewCustomerName("");
    } catch (err) {
      toast(err.message || "Could not add customer.", "error");
    } finally {
      setAddingCustomer(false);
    }
  };

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
    if (isNew) {
      loadCustomers();
      return;
    }
    getQuotationDetail(id).then((d) => {
      setData(d);
      setLines(d.lines.map((l) => ({ ...l })));
      setLoading(false);
      getUpsellSuggestions(id).then(setUpsell).catch(() => setUpsell([]));
      getQuotationNegotiations(id).then(setNegotiations).catch(() => setNegotiations([]));
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
    if (!selectedCustomer) {
      toast("Select a customer first.", "warning");
      return;
    }
    const validLines = lines.filter((l) => l.product_id && Number(l.qty) > 0);
    if (!validLines.length) {
      toast("Add at least one product line before creating the quotation.", "warning");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        customer_name: selectedCustomer.name,
        customer_tier: selectedCustomer.default_tier,
        lines: validLines.map((l) => ({
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

  const handleSaveLines = async (linesOverride, reason) => {
    const source = linesOverride || lines;
    const validLines = source.filter((l) => l.product_id && Number(l.qty) > 0);
    if (!validLines.length) {
      toast("A quotation needs at least one product line — add one before saving.", "warning");
      return false;
    }
    setSaving(true);
    try {
      const payload = {
        lines: validLines.map((l) => ({
          product_id: l.product_id,
          category: l.category,
          qty: Number(l.qty),
          unit_price: Number(l.unit_price),
          discount_pct: Number(l.discount_pct || 0),
        })),
        reason: reason || "Edited from quotation builder",
      };
      const updated = await updateQuotationLines(id, payload);
      setData({ quotation: updated, lines: updated.lines });
      setLines(updated.lines.map((l) => ({ ...l })));
      toast("Line changes saved.", "success");
      return true;
    } catch (err) {
      toast(err.message || "Could not save changes.", "error");
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleAddUpsellSuggestion = async (suggestion) => {
    const product = products.find((p) => p.product_code === suggestion.product_id);
    const newLine = {
      product_id: suggestion.product_id,
      category: product?.category || "Hardware",
      qty: 1,
      unit_price: product?.price || 0,
      discount_pct: 0,
    };
    const nextLines = [...lines, newLine];
    setLines(nextLines);
    setUpsell((prev) => prev.filter((s) => s.product_id !== suggestion.product_id));

    if (isNew) {
      toast(`${suggestion.name || suggestion.product_id} added — save the quotation to persist it.`, "success");
      return;
    }
    const saved = await handleSaveLines(nextLines, `Added upsell suggestion: ${suggestion.name || suggestion.product_id}`);
    if (saved) {
      getUpsellSuggestions(id).then(setUpsell).catch(() => {});
    }
  };

  const handleDismissUpsellSuggestion = (productId) => {
    setUpsell((prev) => prev.filter((s) => s.product_id !== productId));
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const saved = await handleSaveLines();
      if (!saved) return;
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

  const handleRespondNegotiation = async (negotiation, action) => {
    setRespondingId(negotiation.id);
    try {
      const result = await respondToNegotiation(id, negotiation.id, action);
      if (action === "accept") {
        toast(
          result.approval_stage === "confirmed"
            ? "Counter accepted — quotation confirmed."
            : `Counter accepted — routed for approval: ${result.approval_stage.replace("_", " ")} (${result.blended_risk} risk).`,
          "success"
        );
      } else {
        toast("Counter declined. Customer will see this and can propose again.", "success");
      }
      const [refreshed, refreshedNegotiations] = await Promise.all([
        getQuotationDetail(id),
        getQuotationNegotiations(id),
      ]);
      setData(refreshed);
      setLines(refreshed.lines.map((l) => ({ ...l })));
      setNegotiations(refreshedNegotiations);
    } catch (err) {
      toast(err.message || "Could not respond to negotiation.", "error");
    } finally {
      setRespondingId(null);
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
              <label className="df-label">Customer</label>
              <select
                className="df-input text-xs"
                value={selectedCustomerId}
                onChange={(e) => setSelectedCustomerId(e.target.value)}
              >
                <option value="">Select a customer…</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} ({c.default_tier})</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setNewCustomerOpen(true)}
                className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-bold text-brand-700 hover:underline"
              >
                <UserPlus className="h-3 w-3" /> New customer not listed here
              </button>
            </div>
            <div>
              <label className="df-label">Customer Tier</label>
              <div className="df-input text-xs bg-slate-50 text-slate-500 flex items-center cursor-not-allowed">
                {selectedCustomer ? selectedCustomer.default_tier : "Select a customer first"}
              </div>
              <p className="mt-1 text-[10.5px] text-slate-400">
                Tier is earned automatically from closed order volume — never set manually.
              </p>
            </div>
          </div>
        </Panel>

        <LineEditor lines={lines} products={products} onUpdate={updateLine} onAdd={addLine} onRemove={removeLine} />

        {newCustomerOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
            <div className="relative w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl border border-slate-200">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <h2 className="text-base font-bold text-slate-900">Add New Customer</h2>
                <button onClick={() => setNewCustomerOpen(false)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <form onSubmit={handleAddCustomer} className="space-y-3.5">
                <div>
                  <label className="df-label">Company Name *</label>
                  <input
                    required autoFocus className="df-input text-xs"
                    value={newCustomerName}
                    onChange={(e) => setNewCustomerName(e.target.value)}
                    placeholder="e.g. Acme Corp"
                  />
                </div>
                <p className="text-[11px] text-slate-500">
                  New customers always start at <b>Bronze</b> — tier rises automatically as their
                  orders close.
                </p>
                <div className="mt-2 flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button type="button" onClick={() => setNewCustomerOpen(false)} className="df-btn-secondary">Cancel</button>
                  <button type="submit" disabled={addingCustomer} className="df-btn-primary">
                    {addingCustomer ? "Adding..." : "Add Customer"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
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
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
                            s.suggestion_type === "upsell"
                              ? "bg-violet-50 text-violet-700 border border-violet-200"
                              : "bg-sky-50 text-sky-700 border border-sky-200"
                          }`}
                        >
                          {s.suggestion_type === "upsell" ? "Upsell" : "Cross-sell"}
                        </span>
                        <div className="text-xs font-bold text-slate-800">{s.name || s.product_id}</div>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{s.promo_tag || "Recommended pairing"}</div>
                    </div>
                    <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                      +{money(s.margin_delta)} margin
                    </span>
                  </div>
                  {!readOnly && (
                    <div className="mt-2.5 flex gap-2">
                      <button
                        type="button"
                        className="rounded-md bg-brand-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-brand-700"
                        onClick={() => handleAddUpsellSuggestion(s)}
                      >
                        Add to Quote
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-500 hover:bg-slate-50"
                        onClick={() => handleDismissUpsellSuggestion(s.product_id)}
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No upsell suggestions for the current cart.</p>
          )}
        </Panel>
      }
    >
      {negotiations.some((n) => n.status === "pending") && (
        <Panel
          title="Customer Negotiation Requests"
          right={
            <span className="rounded bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700 border border-amber-200">
              Awaiting your response
            </span>
          }
        >
          <div className="space-y-3">
            {negotiations
              .filter((n) => n.status === "pending")
              .map((n) => {
                const line = lines.find((l) => l.id === n.quotation_line_id);
                return (
                  <div key={n.id} className="rounded-xl border border-amber-200 bg-amber-50/40 p-3.5">
                    <div className="text-xs font-bold text-slate-800">
                      {line ? line.product_name || line.product_id : "General request"}
                      {line && ` — currently ${line.discount_pct}% off`}
                    </div>
                    {n.counter_discount_pct != null && (
                      <div className="mt-1 text-xs font-mono font-bold text-brand-700">
                        Customer requests: {n.counter_discount_pct}% off
                      </div>
                    )}
                    {n.message && <div className="mt-1 text-xs text-slate-600 italic">"{n.message}"</div>}
                    <div className="mt-2.5 flex gap-2">
                      <button
                        type="button"
                        disabled={respondingId === n.id}
                        className="rounded-md bg-emerald-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
                        onClick={() => handleRespondNegotiation(n, "accept")}
                      >
                        {respondingId === n.id ? "Working..." : "Accept Counter"}
                      </button>
                      <button
                        type="button"
                        disabled={respondingId === n.id}
                        className="rounded-md border border-slate-300 px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                        onClick={() => handleRespondNegotiation(n, "decline")}
                      >
                        Decline
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        </Panel>
      )}
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
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">{line.category}</span>
                </td>
                <td>
                  {readOnly ? <span className="font-semibold text-slate-700">{line.qty}</span> : (
                    <input type="number" min="1" className="df-input w-16 text-xs py-1" value={line.qty} onChange={(e) => onUpdate(idx, "qty", e.target.value)} />
                  )}
                </td>
                <td>
                  <span className="font-mono text-xs text-slate-700" title="Set by the product's price list — apply a discount below to adjust the customer's price">
                    {money(line.unit_price)}
                  </span>
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
