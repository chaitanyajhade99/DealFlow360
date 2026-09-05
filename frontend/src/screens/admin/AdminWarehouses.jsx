import { useEffect, useState } from "react";
import { Plus, Package, CheckCircle2, X } from "lucide-react";
import { getWarehouses, createWarehouse, updateWarehouse } from "../../api/client";
import AdminNav from "../../components/AdminNav";
import Panel from "../../components/Panel";
import Skeleton from "../../components/Skeleton";
import { useToast } from "../../context/ToastContext";
import { money } from "../../utils";

const emptyForm = { name: "", shipping_cost_per_unit: "0", shipment_fixed_cost: "0", reorder_point: "10", reorder_qty: "40" };

export default function AdminWarehouses() {
  const { toast } = useToast();
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState(emptyForm);

  const load = () => getWarehouses().then(setWarehouses);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast("Give the warehouse a name.", "warning");
      return;
    }
    setSaving(true);
    try {
      const created = await createWarehouse({
        name: formData.name,
        stock: [],
        shipping_cost_per_unit: Number(formData.shipping_cost_per_unit),
        shipment_fixed_cost: Number(formData.shipment_fixed_cost),
        replenishment_rules: { reorder_point: Number(formData.reorder_point), reorder_qty: Number(formData.reorder_qty) },
      });
      setWarehouses((prev) => [...prev, created]);
      setIsModalOpen(false);
      setFormData(emptyForm);
      toast(`Warehouse "${created.name}" created.`, "success");
    } catch (err) {
      toast(err.message || "Could not create warehouse.", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleStockUpdate = async (warehouse, productId, qty) => {
    const stock = warehouse.stock.map((s) => (s.product_id === productId ? { ...s, qty: Number(qty) } : s));
    try {
      const updated = await updateWarehouse(warehouse.id, { ...warehouse, stock });
      setWarehouses((prev) => prev.map((w) => (w.id === warehouse.id ? updated : w)));
    } catch (err) {
      toast(err.message || "Could not update stock.", "error");
    }
  };

  if (loading) return <Skeleton variant="card" count={2} />;

  return (
    <div className="space-y-6 animate-fade-slide-in">
      <AdminNav />
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Warehouse & Fulfillment Setup</h1>
          <p className="mt-1 text-xs text-slate-500">PDF A4 — stock levels, replenishment rules, and shipping cost weighting.</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="df-btn-primary gap-1.5">
          <Plus className="h-4 w-4" /> New Warehouse
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {warehouses.map((w) => (
          <Panel key={w.id} title={w.name} right={<Package className="h-4 w-4 text-slate-400" />}>
            <div className="grid grid-cols-2 gap-3 text-xs mb-4">
              <div className="rounded-lg bg-slate-50 p-2.5">
                <div className="df-label">Shipping / Unit</div>
                <div className="font-mono font-bold">{money(w.shipping_cost_per_unit)}</div>
              </div>
              <div className="rounded-lg bg-slate-50 p-2.5">
                <div className="df-label">Fixed Shipment Cost</div>
                <div className="font-mono font-bold">{money(w.shipment_fixed_cost)}</div>
              </div>
              <div className="rounded-lg bg-slate-50 p-2.5 col-span-2">
                <div className="df-label">Replenishment Rule</div>
                <div className="font-mono text-[11px]">
                  Reorder at {w.replenishment_rules?.reorder_point ?? "—"}, order {w.replenishment_rules?.reorder_qty ?? "—"} units
                </div>
              </div>
            </div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">Stock Levels</div>
            <div className="space-y-1.5">
              {w.stock.map((s) => (
                <div key={s.product_id} className="flex items-center justify-between text-xs">
                  <span className="font-mono text-slate-700">{s.product_id}</span>
                  <input
                    type="number"
                    min="0"
                    defaultValue={s.qty}
                    onBlur={(e) => handleStockUpdate(w, s.product_id, e.target.value)}
                    className="df-input w-24 py-1 text-xs font-mono"
                  />
                </div>
              ))}
              {!w.stock.length && <p className="text-[11px] text-slate-400">No stock rows yet.</p>}
            </div>
          </Panel>
        ))}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h2 className="text-base font-bold text-slate-900">New Warehouse</h2>
              <button onClick={() => setIsModalOpen(false)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"><X className="h-4 w-4" /></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3.5">
              <div>
                <label className="df-label">Warehouse Name *</label>
                <input required className="df-input text-xs" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="e.g. West Coast Depot" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="df-label">Shipping Cost / Unit</label>
                  <input type="number" step="0.01" className="df-input text-xs font-mono" value={formData.shipping_cost_per_unit} onChange={(e) => setFormData({ ...formData, shipping_cost_per_unit: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Fixed Shipment Cost</label>
                  <input type="number" step="0.01" className="df-input text-xs font-mono" value={formData.shipment_fixed_cost} onChange={(e) => setFormData({ ...formData, shipment_fixed_cost: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Reorder Point</label>
                  <input type="number" className="df-input text-xs font-mono" value={formData.reorder_point} onChange={(e) => setFormData({ ...formData, reorder_point: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Reorder Qty</label>
                  <input type="number" className="df-input text-xs font-mono" value={formData.reorder_qty} onChange={(e) => setFormData({ ...formData, reorder_qty: e.target.value })} />
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
