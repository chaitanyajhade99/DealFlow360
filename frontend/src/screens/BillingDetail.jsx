import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Receipt, XCircle, CreditCard, Repeat, Calendar } from "lucide-react";
import { getQuotationDetail } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { code, lineTotal, money, pct } from "../utils";

export default function BillingDetail() {
  const navigate = useNavigate();
  const [data, setData] = useState({ quotation: null, lines: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getQuotationDetail(1042).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, []);

  if (loading || !data.quotation) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const oneTime = data.lines.filter(
    (l) => l.category !== "Subscription" && l.product_id !== "CARE-PLAN-2YR"
  );
  const recurring = data.lines.filter(
    (l) => l.product_id === "CARE-PLAN-2YR" || l.category === "Subscription"
  );

  const oneTimeTotal = oneTime.reduce((s, l) => s + lineTotal(l), 0);
  const recurringTotal = recurring.reduce((s, l) => s + lineTotal(l), 0);

  return (
    <DetailScreen
      title={`Billing Detail · ${data.quotation.customer_name}`}
      subtitle={`${code("Q", data.quotation.id)} · Bifurcated one-time & recurring billing schedules`}
      actions={[
        {
          label: "View Invoice",
          primary: true,
          onClick: () => navigate("/app/invoices/9001"),
        },
        {
          label: "Cancel Subscription",
          variant: "danger",
          onClick: () => {},
        },
      ]}
      banner={{
        title: "Bifurcated billing structures active:",
        body: "Per design spec, One-Time Hardware/Services lines and Recurring Subscription lines are kept in separate dedicated tables without an artificial 'type' column.",
      }}
    >
      {/* Revenue Split Summary */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
              <CreditCard className="h-3.5 w-3.5 text-brand-600" />
              One-Time Capital Invoicing
            </span>
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">
            {money(oneTimeTotal)}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Due on standard Net 30 terms</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
              <Repeat className="h-3.5 w-3.5 text-secondary-600" />
              Annual Recurring Revenue (ARR)
            </span>
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">
            {money(recurringTotal)} <span className="text-xs font-normal text-slate-400">/ yr</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Auto-renews on Jan 15, 2027</div>
        </div>
      </div>

      {/* Table 1: One-time Lines */}
      <Panel
        title="One-Time Hardware & Delivery Lines"
        right={
          <span className="font-mono text-xs font-bold text-slate-900">
            Subtotal: {money(oneTimeTotal)}
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Product Item</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Applied Discount</th>
                <th>Line Total</th>
              </tr>
            </thead>
            <tbody>
              {oneTime.map((l) => (
                <tr key={l.id}>
                  <td className="font-mono text-xs font-bold text-slate-900">{l.product_id}</td>
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

      {/* Table 2: Recurring Lines */}
      <Panel
        title="Recurring Subscription & Support Plans"
        right={
          <span className="font-mono text-xs font-bold text-slate-900">
            ARR: {money(recurringTotal)}
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Subscription Plan</th>
                <th>Seat Quantity</th>
                <th>Rate / Seat</th>
                <th>Cadence</th>
                <th>Annual Total</th>
              </tr>
            </thead>
            <tbody>
              {recurring.map((l) => (
                <tr key={l.id}>
                  <td>
                    <div className="font-bold text-xs text-slate-900">{l.product_id}</div>
                    <div className="text-[11px] text-slate-400">Two-year coverage warranty</div>
                  </td>
                  <td className="font-semibold text-slate-700">{l.qty} seats</td>
                  <td className="font-mono text-xs text-slate-700">{money(l.unit_price)} / yr</td>
                  <td>
                    <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-[10px] font-bold text-indigo-700 border border-indigo-200">
                      Yearly
                    </span>
                  </td>
                  <td className="font-mono text-xs font-bold text-slate-900">{money(lineTotal(l))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </DetailScreen>
  );
}

