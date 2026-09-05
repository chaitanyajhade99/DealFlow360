import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getInvoiceDetail, payInvoice } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import StatusStepper from "../components/StatusStepper";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, date, lineTotal, money, pct } from "../utils";

export default function InvoiceDetail() {
  const { id } = useParams();
  const { toast } = useToast();
  const [data, setData] = useState({ invoice: null, quotation: null, lines: [] });
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [manualConfirmOpen, setManualConfirmOpen] = useState(false);
  const [manualReference, setManualReference] = useState("");

  const load = () => getInvoiceDetail(id).then(setData);

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading || !data.invoice) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const isPaid = data.invoice.status === "paid";
  const currentStep = isPaid ? 3 : 2;

  const handleRecordManualPayment = async () => {
    if (!manualReference.trim()) {
      toast("Enter the bank reference / reason before confirming.", "warning");
      return;
    }
    setBusy(true);
    try {
      await payInvoice(data.invoice.id, {
        amount: data.invoice.amount,
        method: `bank_transfer: ${manualReference.trim()}`,
      });
      toast(`Manual payment of ${money(data.invoice.amount)} recorded — invoice marked paid.`, "success");
      setManualConfirmOpen(false);
      setManualReference("");
      load();
    } catch (err) {
      toast(err.message || "Could not record payment.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <DetailScreen
      title={`Invoice Commercial Record · ${code("INV", data.invoice.id)}`}
      subtitle={`${data.quotation?.customer_name || "Customer"} · Source Quote ${code(
        "Q",
        data.invoice.quotation_id
      )} · Due ${date(data.invoice.due_date)}`}
      actions={[]}
      banner={{
        title: isPaid ? "Invoice Settlement Complete:" : "Receivable Outstanding:",
        body: isPaid
          ? `Commercial invoice amount of ${money(data.invoice.amount)} is marked as PAID.`
          : `Commercial invoice amount of ${money(
              data.invoice.amount
            )} is marked as UNPAID. Payment is collected from the customer directly, through their portal (Razorpay Checkout) — this screen is view-only for the ops team, plus a gated manual-reconciliation override below for genuine offline payments.`,
      }}
    >
      {/* Order-to-Payment Lifecycle Stepper */}
      <Panel title="Order-to-Cash Lifecycle Progress">
        <div className="py-2">
          <StatusStepper
            steps={["Order Confirmed", "Shipped", "Invoiced", "Paid"]}
            currentIndex={currentStep}
          />
        </div>
      </Panel>

      {/* Invoice Line Items */}
      <Panel
        title="Invoiced Commercial Line Items"
        right={
          <span className="font-mono text-xs font-bold text-slate-900">
            Total: {money(data.invoice.amount)}
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Product Code</th>
                <th>Category</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Discount</th>
                <th>Billed Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l, idx) => (
                <tr key={l.id} className={`animate-stagger-${idx + 1}`}>
                  <td className="font-mono text-xs font-bold text-slate-900">{l.product_id}</td>
                  <td>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                      {l.category}
                    </span>
                  </td>
                  <td className="font-semibold text-slate-700">{l.qty}</td>
                  <td className="font-mono text-xs text-slate-700">{money(l.unit_price)}</td>
                  <td className="font-mono text-xs font-semibold text-brand-700">{pct(l.discount_pct)}</td>
                  <td className="font-mono text-xs font-bold text-slate-900">{money(lineTotal(l))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Invoice Summary Card */}
      <Panel title="Commercial Settlement Summary">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3.5">
            <div className="df-label">Settlement Status</div>
            <div className="mt-1">
              <StatusBadge value={isPaid ? "paid" : "unpaid"} />
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {isPaid ? "Full amount cleared" : "Awaiting customer wire"}
            </div>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3.5">
            <div className="df-label">Gross Amount Payable</div>
            <div className="font-mono text-xl font-black text-slate-900 mt-0.5">
              {money(data.invoice.amount)}
            </div>
            <div className="text-[11px] text-slate-400">INR currency</div>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3.5">
            <div className="df-label">Payment Due Date</div>
            <div className="text-sm font-bold text-slate-800 font-mono mt-0.5">
              {date(data.invoice.due_date)}
            </div>
            <div className="text-[11px] text-slate-400">Net 30 terms</div>
          </div>
        </div>

        {!isPaid && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setManualConfirmOpen(true)}
              className="text-[11px] font-semibold text-slate-400 hover:text-slate-600 hover:underline"
            >
              Finance: mark as paid manually (bank transfer already received outside DealFlow360)
            </button>
          </div>
        )}
      </Panel>

      {manualConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200">
            <h2 className="text-base font-bold text-slate-900">Confirm manual payment</h2>
            <p className="mt-1.5 text-xs text-slate-500">
              This marks the invoice paid without going through Razorpay. Only use this when the
              customer has genuinely already paid outside the platform (e.g. a bank wire) — enter
              the reference so it's traceable in the audit trail.
            </p>
            <label className="df-label mt-4">Bank Reference / Reason *</label>
            <input
              className="df-input text-xs"
              value={manualReference}
              onChange={(e) => setManualReference(e.target.value)}
              placeholder="e.g. Wire ref #WT-88213"
              autoFocus
            />
            <div className="mt-5 flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => { setManualConfirmOpen(false); setManualReference(""); }}
                className="df-btn-secondary"
              >
                Cancel
              </button>
              <button type="button" onClick={handleRecordManualPayment} disabled={busy} className="df-btn-primary">
                {busy ? "Recording..." : "Confirm & Mark Paid"}
              </button>
            </div>
          </div>
        </div>
      )}
    </DetailScreen>
  );
}

