import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  SlidersHorizontal,
  Save,
  Layers,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import { getFulfillmentDetail, overrideFulfillment, resetFulfillment } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { useRole } from "../context/RoleContext";
import { code, money } from "../utils";

// Builds { [product_id]: { [warehouse_id]: qty } } from the persisted splits
// so the per-line, per-warehouse inputs start pre-filled with whatever's
// currently allocated (suggested or a prior manual override).
function splitsToGrid(splits) {
  const grid = {};
  for (const s of splits || []) {
    if (s.is_backorder) continue;
    grid[s.product_id] = grid[s.product_id] || {};
    grid[s.product_id][s.warehouse_id] = s.qty;
  }
  return grid;
}

export default function FulfillmentDetail() {
  const { id } = useParams();
  const { toast } = useToast();
  const { isFinance, isAdmin } = useRole();
  // PDF section 3: Finance/Operations "manages warehouse fulfillment splits
  // and backorder decisions" -- a Sales Rep only tracks progress (read-only).
  // Enforced server-side too (POST .../override|reset are Finance/Admin-only);
  // this just keeps a rep from seeing edit controls for an action the API
  // will reject anyway.
  const canOverride = isFinance || isAdmin;
  const [data, setData] = useState({ quotation: null, lines: [], fulfillment: null, warehouses: [] });
  // "editing" = the override FORM is open (only ever true for Finance/Admin).
  // Whether the persisted record IS a manual override is a separate fact,
  // read straight from data.fulfillment.is_manual_override below -- keeping
  // these distinct means a rep loading an already-overridden quotation can
  // never end up with edit inputs rendered, since editing always starts false.
  const [editing, setEditing] = useState(false);
  const [grid, setGrid] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = () =>
    getFulfillmentDetail(id).then((d) => {
      setData(d);
      setGrid(splitsToGrid(d.fulfillment?.splits));
      setEditing(false);
      setLoading(false);
    });

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading || !data.quotation) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const splits = data.fulfillment?.splits || [];
  const backorders = data.fulfillment?.backorders || [];
  const totalQty = data.lines.reduce((s, l) => s + l.qty, 0);
  const totalAllocated = splits.filter((s) => !s.is_backorder).reduce((s, x) => s + Number(x.qty || 0), 0);
  const totalCost = splits.reduce((s, x) => s + Number(x.cost || 0), 0);
  const coveragePct = totalQty > 0 ? Math.min(100, Math.round((totalAllocated / totalQty) * 100)) : 100;
  const isComplete = backorders.length === 0;
  const isManualOverride = Boolean(data.fulfillment?.is_manual_override);

  const setCell = (productId, warehouseId, qty) => {
    setGrid((prev) => ({
      ...prev,
      [productId]: { ...(prev[productId] || {}), [warehouseId]: qty },
    }));
  };

  const handleSaveOverride = async () => {
    const lines = [];
    for (const line of data.lines) {
      for (const wh of data.warehouses) {
        const qty = Number(grid[line.product_id]?.[wh.id] || 0);
        if (qty > 0) lines.push({ product_id: line.product_id, warehouse_id: wh.id, qty });
      }
    }
    if (!lines.length) {
      toast("Allocate at least one unit to at least one warehouse first.", "warning");
      return;
    }
    setSaving(true);
    try {
      const updated = await overrideFulfillment(id, lines);
      setData((prev) => ({ ...prev, fulfillment: updated }));
      setGrid(splitsToGrid(updated.splits));
      toast("Manual override saved — this is now the persisted fulfillment plan.", "success");
    } catch (err) {
      toast(err.message || "Could not save override.", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleAcceptSuggested = async () => {
    setSaving(true);
    try {
      const updated = await resetFulfillment(id);
      setData((prev) => ({ ...prev, fulfillment: updated }));
      setGrid(splitsToGrid(updated.splits));
      setEditing(false);
      toast("Reverted to the algorithmic suggested split.", "success");
    } catch (err) {
      toast(err.message || "Could not reset fulfillment.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <DetailScreen
      title={`Fulfillment Allocation · ${code("Q", data.quotation.id)}`}
      subtitle={`${data.quotation.customer_name} · Multi-depot routing and inventory readiness`}
      actions={
        canOverride
          ? [
              { label: "Accept Suggested Split", primary: !editing, onClick: handleAcceptSuggested },
              { label: editing ? "Cancel Override" : "Manual Override", primary: editing, onClick: () => setEditing((v) => !v) },
            ]
          : []
      }
      banner={{
        title: isComplete
          ? "Warehouse split allocation verified:"
          : "Stock allocation variance detected:",
        body: `${totalAllocated} of ${totalQty} requested units allocated (${coveragePct}% coverage). Total estimated shipping cost: ${money(
          totalCost
        )}.${backorders.length ? ` ${backorders.reduce((s, b) => s + b.qty, 0)} unit(s) on backorder.` : ""}`,
      }}
    >
      <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="font-bold text-slate-700 flex items-center gap-1.5">
            <Layers className="h-4 w-4 text-brand-600" />
            Stock Fulfillment Progress
          </span>
          <span className="font-mono font-bold text-brand-700">{totalAllocated} / {totalQty} Units ({coveragePct}%)</span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${
              isComplete ? "bg-emerald-500" : "bg-amber-500"
            }`}
            style={{ width: `${coveragePct}%` }}
          />
        </div>
      </div>

      <Panel
        title="Multi-Warehouse Inventory Allocation"
        right={
          isManualOverride ? (
            <span className="flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
              <SlidersHorizontal className="h-3 w-3" /> Manual Override
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] font-bold text-brand-700 bg-brand-50 px-2.5 py-0.5 rounded border border-brand-200">
              Algorithmic Split (Optimal)
            </span>
          )
        }
      >
        <div className="space-y-5">
          {data.lines.map((line) => {
            // Editing (Finance/Admin only) needs every warehouse as a
            // candidate destination, even ones not currently allocated.
            // Read-only view (everyone else, or Finance/Admin before
            // clicking "Manual Override") is built purely from the
            // persisted splits -- each row already carries its own
            // warehouse name, so it renders correctly even when
            // data.warehouses is empty (a Sales Rep's GET /warehouses is
            // 403'd server-side and resolves to []).
            const rowsForLine = editing
              ? data.warehouses.map((w) => ({ warehouse_id: w.id, warehouse: w.name, w }))
              : splits.filter((s) => s.product_id === line.product_id && !s.is_backorder);
            const lineBackorder = backorders.find((b) => b.product_id === line.product_id);

            return (
              <div key={line.id} className="rounded-lg border border-slate-200 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-xs font-bold text-slate-800">
                    {line.product_id} <span className="font-normal text-slate-400">— {line.qty} units required</span>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="df-table">
                    <thead>
                      <tr>
                        <th>Depot Facility</th>
                        <th>Allocated Qty</th>
                        <th>Est. Freight Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rowsForLine.map((row) => {
                        const qty = editing ? grid[line.product_id]?.[row.warehouse_id] || 0 : row.qty;
                        const cost = editing
                          ? (qty > 0 ? Number(row.w.shipment_fixed_cost) + Number(row.w.shipping_cost_per_unit) * qty : 0)
                          : row.cost;
                        return (
                          <tr key={row.warehouse_id}>
                            <td className="font-bold text-xs text-slate-900">{row.warehouse}</td>
                            <td>
                              {editing ? (
                                <input
                                  aria-label={`Allocate ${line.product_id} from ${row.warehouse}`}
                                  className="df-input w-24 py-1 px-2.5 text-xs font-mono font-bold border-amber-300 bg-amber-50/50 focus:border-amber-500 focus:ring-amber-200"
                                  type="number"
                                  min="0"
                                  value={qty}
                                  onChange={(e) => setCell(line.product_id, row.warehouse_id, e.target.value)}
                                />
                              ) : (
                                <span className="font-mono text-xs font-bold text-slate-900">{qty} units</span>
                              )}
                            </td>
                            <td className="font-mono text-xs text-slate-700">{money(cost)}</td>
                          </tr>
                        );
                      })}
                      {!rowsForLine.length && !editing && (
                        <tr>
                          <td colSpan={3} className="text-center text-xs text-slate-400 py-3">
                            No allocation yet.
                          </td>
                        </tr>
                      )}
                      {lineBackorder && (
                        <tr>
                          <td className="font-bold text-xs text-red-700">Backorder</td>
                          <td className="font-mono text-xs font-bold text-red-700">{lineBackorder.qty} units short</td>
                          <td>—</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>

        {editing && (
          <div className="mt-4 flex justify-end gap-2">
            <button onClick={() => { setEditing(false); setGrid(splitsToGrid(splits)); }} className="df-btn-secondary gap-1.5">
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Discard Changes</span>
            </button>
            <button onClick={handleSaveOverride} disabled={saving} className="df-btn-primary gap-1.5" aria-label="Save manual split">
              <Save className="h-3.5 w-3.5" />
              <span>{saving ? "Saving..." : "Save Manual Override"}</span>
            </button>
          </div>
        )}
      </Panel>

      <div className="flex items-start gap-2.5 rounded-lg border border-sky-200 bg-sky-50/60 p-3 text-xs text-sky-900">
        <AlertCircle className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
        <div>
          {canOverride
            ? <>Every allocation above is validated against each warehouse's real live stock and the quotation's actual required quantities before it's saved — <code className="font-mono">POST /fulfillment/{data.quotation.id}/override</code>. Under-allocating a line creates a real backorder row, same as the suggested split.</>
            : "Warehouse fulfillment splits and backorder decisions are managed by Finance/Operations — this view is read-only."}
        </div>
      </div>
    </DetailScreen>
  );
}
