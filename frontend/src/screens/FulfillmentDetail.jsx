import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Building,
  CheckCircle2,
  SlidersHorizontal,
  Save,
  Truck,
  Layers,
  AlertCircle,
} from "lucide-react";
import { getFulfillmentDetail, saveFulfillmentSplit } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { code, money } from "../utils";

export default function FulfillmentDetail() {
  const { id } = useParams();
  const [data, setData] = useState({
    quotation: null,
    lines: [],
    fulfillment: null,
    warehouses: [],
  });
  const [manual, setManual] = useState(false);
  const [splits, setSplits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savedFeedback, setSavedFeedback] = useState(false);

  useEffect(() => {
    getFulfillmentDetail(id).then((d) => {
      setData(d);
      setSplits(d.fulfillment?.splits || []);
      setLoading(false);
    });
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

  const totalQty = data.lines.reduce((s, l) => s + l.qty, 0);
  const totalAllocated = splits.reduce((s, x) => s + Number(x.qty || 0), 0);
  const totalCost = splits.reduce((s, x) => s + Number(x.cost || 0), 0);
  const coveragePct = totalQty > 0 ? Math.min(100, Math.round((totalAllocated / totalQty) * 100)) : 100;
  const isComplete = totalAllocated >= totalQty;

  const handleSave = async () => {
    await saveFulfillmentSplit(data.quotation.id, splits);
    setSavedFeedback(true);
    setTimeout(() => setSavedFeedback(false), 3000);
  };

  return (
    <DetailScreen
      title={`Fulfillment Allocation · ${code("Q", data.quotation.id)}`}
      subtitle={`${data.quotation.customer_name} · Multi-depot routing and inventory readiness`}
      actions={[
        {
          label: "Accept Suggested Split",
          primary: !manual,
          onClick: () => {
            setManual(false);
            setSplits(data.fulfillment?.splits || []);
          },
        },
        {
          label: manual ? "Lock Override" : "Manual Override",
          primary: manual,
          onClick: () => setManual((v) => !v),
        },
      ]}
      banner={{
        title: isComplete
          ? "Warehouse split allocation verified:"
          : "Stock allocation variance detected:",
        body: `${totalAllocated} of ${totalQty} requested units allocated (${coveragePct}% coverage). Total estimated shipping cost: ${money(
          totalCost
        )}.`,
      }}
    >
      {/* Allocation Progress Bar Banner */}
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

      {savedFeedback && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2 text-xs text-emerald-900 animate-fade-slide-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>Manual inventory split override saved locally.</span>
          </div>
        </div>
      )}

      {/* Order Lines */}
      <Panel title="Order Line Items & Demand Requirements">
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Product Code</th>
                <th>Category</th>
                <th>Requested Qty</th>
                <th>Unit Price</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l) => (
                <tr key={l.id}>
                  <td className="font-mono text-xs font-bold text-slate-900">{l.product_id}</td>
                  <td>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                      {l.category}
                    </span>
                  </td>
                  <td className="font-bold text-slate-800">{l.qty} units</td>
                  <td className="font-mono text-xs text-slate-700">{money(l.unit_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Warehouse Split */}
      <Panel
        title="Multi-Warehouse Inventory Allocation"
        right={
          manual ? (
            <span className="flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
              <SlidersHorizontal className="h-3 w-3" /> Manual Override Active
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] font-bold text-brand-700 bg-brand-50 px-2.5 py-0.5 rounded border border-brand-200">
              Algorithmic Split (Optimal)
            </span>
          )
        }
      >
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Depot Facility</th>
                <th>Allocated Quantity</th>
                <th>Estimated Freight Cost</th>
                <th>Routing Mode</th>
              </tr>
            </thead>
            <tbody>
              {data.warehouses.map((w) => {
                const existing = splits.find((s) => s.warehouse_id === w.id) || {
                  warehouse_id: w.id,
                  qty: 0,
                  cost: 0,
                };
                return (
                  <tr key={w.id}>
                    <td>
                      <div className="font-bold text-xs text-slate-900">{w.name}</div>
                      <div className="text-[11px] text-slate-400">Warehouse #{w.id}</div>
                    </td>
                    <td>
                      {manual ? (
                        <div className="relative w-32">
                          <input
                            aria-label={`Allocated quantity for ${w.name}`}
                            className="df-input py-1 px-2.5 text-xs font-mono font-bold border-amber-300 bg-amber-50/50 focus:border-amber-500 focus:ring-amber-200"
                            type="number"
                            min="0"
                            value={existing.qty}
                            onChange={(e) =>
                              setSplits((prev) =>
                                prev.some((x) => x.warehouse_id === w.id)
                                  ? prev.map((x) =>
                                      x.warehouse_id === w.id
                                        ? { ...x, qty: Number(e.target.value) }
                                        : x
                                    )
                                  : [
                                      ...prev,
                                      {
                                        ...existing,
                                        qty: Number(e.target.value),
                                      },
                                    ]
                              )
                            }
                          />
                        </div>
                      ) : (
                        <span className="font-mono text-xs font-bold text-slate-900">
                          {existing.qty} units
                        </span>
                      )}
                    </td>
                    <td className="font-mono text-xs text-slate-700">{money(existing.cost)}</td>
                    <td>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          manual
                            ? "bg-amber-100 text-amber-800 border border-amber-200"
                            : "bg-brand-50 text-brand-700 border border-brand-200"
                        }`}
                      >
                        {manual ? "Editable Override" : "Algorithmic"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {manual && (
          <div className="mt-4 flex justify-end">
            <button onClick={handleSave} className="df-btn-primary gap-1.5" aria-label="Save manual split">
              <Save className="h-3.5 w-3.5" />
              <span>Save Manual Override</span>
            </button>
          </div>
        )}
      </Panel>

      <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50/60 p-3 text-xs text-amber-800">
        <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <b>Contract note:</b> Manual Override is frontend-managed in this release because the supplied API contract does not specify a fulfillment write endpoint.
        </div>
      </div>
    </DetailScreen>
  );
}

