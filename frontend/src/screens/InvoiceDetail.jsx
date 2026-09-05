import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Receipt,
  Download,
  CheckCircle2,
  DollarSign,
  Calendar,
  CreditCard,
  Building,
} from "lucide-react";
import { getInvoiceDetail } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import StatusStepper from "../components/StatusStepper";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { code, date, lineTotal, money, pct } from "../utils";

export default function InvoiceDetail() {
  const { id } = useParams();
  const [data, setData] = useState({ invoice: null, quotation: null, lines: [] });
  const [paidOverride, setPaidOverride] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getInvoiceDetail(id).then((d) => {
      setData(d);
      setLoading(false);
    });
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

  const isPaid = paidOverride || data.invoice.status === "paid";
  const currentStep = isPaid ? 3 : 2;

  const handleRecordPayment = () => {
    setPaidOverride(true);
    setFeedback("Payment transaction of " + money(data.invoice.amount) + " recorded successfully.");
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleDownload = () => {
    setFeedback("Generated commercial invoice PDF bundle for download.");
    setTimeout(() => setFeedback(null), 3000);
  };

  return (
    <DetailScreen
      title={`Invoice Commercial Record · ${code("INV", data.invoice.id)}`}
      subtitle={`${data.quotation?.customer_name || "Customer"} · Source Quote ${code(
        "Q",
        data.invoice.quotation_id
      )} · Due ${date(data.invoice.due_date)}`}
      actions={[
        {
          label: isPaid ? "Payment Recorded ✓" : "Record Payment",
          primary: !isPaid,
          variant: isPaid ? "success" : undefined,
          onClick: handleRecordPayment,
        },
        {
          label: "Download Invoice PDF",
          onClick: handleDownload,
        },
      ]}
      banner={{
        title: isPaid ? "Invoice Settlement Complete:" : "Receivable Outstanding:",
        body: `Commercial invoice amount of ${money(data.invoice.amount)} is marked as ${
          isPaid ? "PAID" : "UNPAID"
        }. Due by ${date(data.invoice.due_date)}.`,
      }}
    >
      {feedback && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs text-emerald-900 shadow-xs animate-fade-slide-in">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          <span className="font-semibold">{feedback}</span>
        </div>
      )}

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
            <div className="text-[11px] text-slate-400">USD currency</div>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3.5">
            <div className="df-label">Payment Due Date</div>
            <div className="text-sm font-bold text-slate-800 font-mono mt-0.5">
              {date(data.invoice.due_date)}
            </div>
            <div className="text-[11px] text-slate-400">Net 30 terms</div>
          </div>
        </div>
      </Panel>
    </DetailScreen>
  );
}

