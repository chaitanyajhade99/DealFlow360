import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Info } from "lucide-react";
import {
  getPortalQuotations,
  getPortalQuotationDetail,
  submitNegotiationRequest,
  confirmPortalQuotation,
  previewPortalQuotationPdf,
} from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, lineTotal, money } from "../utils";

// A customer can request changes on anything that isn't a dead end
// (rejected) -- this intentionally includes "confirmed": a quotation with no
// risky discounts auto-confirms the moment a rep submits it (no internal
// approval was needed), so excluding "confirmed" here would mean a clean
// quote reaches the customer with no chance to ever negotiate it. The
// backend itself has no status restriction on POST .../negotiate.
const NEGOTIABLE_STATUSES = ["draft", "pending_approval", "negotiation", "approved", "confirmed"];

// PDF B8 defines exactly three customer-facing states: "Sent, Under
// Negotiation, Confirmed" -- internal enum values like "pending_approval",
// and internal risk vocabulary (LOW/MEDIUM/HIGH), belong to the workspace,
// not this screen (PDF section 7: the portal "must be a real, separate,
// restricted view, not just another internal screen with a different
// label"). This maps every backend Quotation.status onto that customer
// vocabulary so nothing internal leaks through here.
const CUSTOMER_STATUS = {
  draft: { label: "Sent", tone: "bg-slate-100 text-slate-700 border-slate-200" },
  pending_approval: { label: "Under Review", tone: "bg-amber-50 text-amber-800 border-amber-200" },
  returned: { label: "Under Review", tone: "bg-amber-50 text-amber-800 border-amber-200" },
  approved: { label: "Under Review", tone: "bg-amber-50 text-amber-800 border-amber-200" },
  negotiation: { label: "Under Negotiation", tone: "bg-indigo-50 text-indigo-800 border-indigo-200" },
  confirmed: { label: "Confirmed", tone: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  rejected: { label: "Rejected", tone: "bg-rose-50 text-rose-800 border-rose-200" },
};

function customerStatus(status) {
  return CUSTOMER_STATUS[status] || { label: "Sent", tone: "bg-slate-100 text-slate-700 border-slate-200" };
}

export default function PortalNegotiation() {
  const { quotationId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [allQuotations, setAllQuotations] = useState([]);
  const [data, setData] = useState({ quotation: null, lines: [] });
  const [comments, setComments] = useState({});
  const [counters, setCounters] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [previewingPdf, setPreviewingPdf] = useState(false);

  useEffect(() => {
    getPortalQuotations().then(setAllQuotations).catch(() => setAllQuotations([]));
  }, []);

  const activeId =
    quotationId ||
    allQuotations.find((q) => NEGOTIABLE_STATUSES.includes(q.status))?.id ||
    allQuotations[0]?.id;

  useEffect(() => {
    if (!activeId) {
      if (allQuotations.length === 0 && !loading) return;
      return;
    }
    setLoading(true);
    getPortalQuotationDetail(activeId).then((d) => {
      setData(d);
      setLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, allQuotations.length]);

  if (allQuotations.length === 0 && !loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
        No quotations found for your account yet.
      </div>
    );
  }

  if (loading || !data.quotation) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const { quotation, lines } = data;
  const total = lines.reduce((s, l) => s + lineTotal(l), 0);
  const isNegotiable = NEGOTIABLE_STATUSES.includes(quotation.status);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      for (const line of lines) {
        if (counters[line.id] && Number(counters[line.id]) <= Number(line.discount_pct)) {
          toast(
            `${line.product_name || line.product_id}: a counter discount must be higher than the current ${line.discount_pct}% — that's the point of a counter-offer.`,
            "warning"
          );
          setSubmitting(false);
          return;
        }
      }
      const requests = [];
      for (const line of lines) {
        if (comments[line.id] || counters[line.id]) {
          requests.push(
            submitNegotiationRequest(quotation.id, {
              quotation_line_id: line.id,
              message: comments[line.id] || `Requested ${counters[line.id]}% discount on ${line.product_id}`,
              counter_discount_pct: counters[line.id] ? Number(counters[line.id]) : null,
            })
          );
        }
      }
      if (!requests.length) {
        toast("Add a comment or counter-discount to at least one line first.", "warning");
        setSubmitting(false);
        return;
      }
      await Promise.all(requests);
      toast("Change request submitted to the account sales team.", "success");
      setComments({});
      setCounters({});
      const refreshed = await getPortalQuotationDetail(quotation.id);
      setData(refreshed);
    } catch (err) {
      toast(err.message || "Could not submit request.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePreviewPdf = async () => {
    setPreviewingPdf(true);
    try {
      await previewPortalQuotationPdf(quotation.id);
    } catch (err) {
      toast(err.message || "Could not open PDF preview.", "error");
    } finally {
      setPreviewingPdf(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      const approval = await confirmPortalQuotation(quotation.id);
      if (approval.stage === "confirmed") {
        toast("Quotation confirmed! Order routed for fulfillment processing.", "success");
      } else {
        toast(
          "These terms need a bit more review before they're finalized — your account team has been notified and will update you here.",
          "warning"
        );
      }
      const refreshed = await getPortalQuotationDetail(quotation.id);
      setData(refreshed);
    } catch (err) {
      toast(err.message || "Could not confirm quotation.", "error");
    } finally {
      setConfirming(false);
    }
  };

  const status = customerStatus(quotation.status);

  return (
    <DetailScreen
      title={`Quotation ${code("Q", quotation.id)}`}
      subtitle={`${quotation.customer_name} · Status: ${status.label}`}
      actions={[
        { label: previewingPdf ? "Opening..." : "Preview Quotation PDF", onClick: handlePreviewPdf },
        ...(isNegotiable
          ? [
              { label: submitting ? "Sending..." : "Submit Request", onClick: handleSubmit },
              ...(quotation.status === "confirmed"
                ? []
                : [{ label: confirming ? "Confirming..." : "Confirm Quotation", primary: true, onClick: handleConfirm }]),
            ]
          : []),
      ]}
      banner={{
        title: `Status: ${status.label}`,
        body: "If your final terms exceed approval thresholds, this quotation automatically re-enters the approval flow — no email back-and-forth needed.",
      }}
    >
      {allQuotations.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {allQuotations.map((q) => {
            const qStatus = customerStatus(q.status);
            return (
              <button
                key={q.id}
                onClick={() => navigate(`/portal/${q.id}`)}
                className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${
                  q.id === quotation.id ? "border-indigo-400 bg-indigo-50 text-indigo-800" : "border-slate-200 bg-white text-slate-600"
                }`}
              >
                {code("Q", q.id)} ·{" "}
                <span className={`df-badge ml-1 ${qStatus.tone}`}>{qStatus.label}</span>
              </button>
            );
          })}
        </div>
      )}

      <Panel title="Quotation Lines" right={<span className="font-mono text-sm font-black text-slate-900">{money(total)}</span>}>
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Discount</th>
                <th>Line Total</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.id}>
                  <td className="font-mono text-xs font-bold text-slate-900">{l.product_name || l.product_id}</td>
                  <td className="text-xs font-semibold text-slate-700">{l.qty}</td>
                  <td className="font-mono text-xs text-slate-700">{money(l.unit_price)}</td>
                  <td className="font-mono text-xs font-semibold text-brand-700">{l.discount_pct}%</td>
                  <td className="font-mono text-xs font-bold text-slate-900">{money(lineTotal(l))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {isNegotiable && (
        <Panel title="Request Changes or Counter a Discount">
          <div className="space-y-3">
            {lines.map((l) => (
              <div key={l.id} className="rounded-lg border border-slate-200 p-3">
                <div className="text-xs font-bold text-slate-800 mb-2">{l.product_name || l.product_id} (currently {l.discount_pct}% off)</div>
                <div className="grid gap-2 sm:grid-cols-[1fr_140px]">
                  <input
                    className="df-input text-xs"
                    placeholder="Comment or question…"
                    value={comments[l.id] || ""}
                    onChange={(e) => setComments((prev) => ({ ...prev, [l.id]: e.target.value }))}
                  />
                  <input
                    type="number"
                    min={Number(l.discount_pct) + 0.1}
                    max={100}
                    step="0.1"
                    className="df-input text-xs"
                    placeholder={`> ${l.discount_pct}%`}
                    title={`Must be higher than the current ${l.discount_pct}% discount`}
                    value={counters[l.id] || ""}
                    onChange={(e) => setCounters((prev) => ({ ...prev, [l.id]: e.target.value }))}
                  />
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      <div className="flex items-start gap-2.5 rounded-lg border border-sky-200 bg-sky-50/60 p-3 text-xs text-sky-900">
        <Info className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
        <div>Every action on this page calls the real backend — <code className="font-mono">POST /portal/quotations/{quotation.id}/negotiate</code> and <code className="font-mono">/confirm</code>.</div>
      </div>
    </DetailScreen>
  );
}
