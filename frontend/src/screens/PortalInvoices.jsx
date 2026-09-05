import { useEffect, useState } from "react";
import { Receipt, CreditCard, CheckCircle2 } from "lucide-react";
import { getPortalInvoices, createPortalRazorpayOrder, verifyPortalRazorpayPayment } from "../api/client";
import ListScreen from "../components/ListScreen";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, date, money, loadRazorpayScript } from "../utils";

export default function PortalInvoices() {
  const { toast } = useToast();
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [payingId, setPayingId] = useState(null);

  const load = () => getPortalInvoices().then(setInvoices);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const handlePay = async (invoice) => {
    setPayingId(invoice.id);
    try {
      const loaded = await loadRazorpayScript();
      if (!loaded) throw new Error("Could not load Razorpay checkout script.");
      const order = await createPortalRazorpayOrder(invoice.id);
      const rzp = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        order_id: order.order_id,
        name: "DealFlow360",
        description: `Invoice ${code("INV", invoice.id)}`,
        theme: { color: "#4338ca" },
        handler: async (response) => {
          try {
            await verifyPortalRazorpayPayment(invoice.id, {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            toast("Payment verified — thank you! Invoice marked paid.", "success");
            load();
          } catch (err) {
            toast(err.message || "Payment verification failed.", "error");
          } finally {
            setPayingId(null);
          }
        },
        modal: { ondismiss: () => setPayingId(null) },
      });
      rzp.on("payment.failed", () => {
        toast("Payment failed or was cancelled.", "error");
        setPayingId(null);
      });
      rzp.open();
    } catch (err) {
      toast(err.message || "Could not start checkout.", "error");
      setPayingId(null);
    }
  };

  if (loading) return <Skeleton variant="card" count={3} />;

  return (
    <ListScreen
      title="Billing & Invoices"
      subtitle="Every invoice raised against your account. Pay securely with Razorpay."
      columns={[
        { key: "id", label: "Invoice" },
        { key: "amount", label: "Amount" },
        { key: "due_date", label: "Due Date" },
        { key: "status", label: "Status" },
        { key: "action", label: "" },
      ]}
      rows={invoices}
      banner={{
        title: "You pay, we verify:",
        body: "Payments here go through Razorpay Checkout and are verified by signature on our server before an invoice is ever marked paid.",
      }}
      renderCell={(row, column) => {
        if (column.key === "id") return (
          <div className="flex items-center gap-2">
            <Receipt className="h-3.5 w-3.5 text-slate-400" />
            <span className="font-mono text-xs font-bold text-slate-900">{code("INV", row.id)}</span>
          </div>
        );
        if (column.key === "amount") return <span className="font-mono text-xs font-bold text-slate-900">{money(row.amount)}</span>;
        if (column.key === "due_date") return <span className="font-mono text-[11px] text-slate-500">{date(row.due_date)}</span>;
        if (column.key === "status") return <StatusBadge value={row.status} />;
        if (column.key === "action") {
          if (row.status === "paid") {
            return <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" /> Paid</span>;
          }
          return (
            <button
              onClick={() => handlePay(row)}
              disabled={payingId === row.id}
              className="df-btn-primary !py-1 !px-2.5 text-[11px] gap-1"
            >
              <CreditCard className="h-3.5 w-3.5" />
              {payingId === row.id ? "Opening..." : "Pay Now"}
            </button>
          );
        }
        return row[column.key];
      }}
    />
  );
}
