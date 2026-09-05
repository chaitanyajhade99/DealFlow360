import { useEffect, useState } from "react";
import {
  Send,
  CheckCircle2,
  MessageSquare,
  Sparkles,
  Check,
  Building,
  Info,
} from "lucide-react";
import {
  getNegotiationRequests,
  getQuotationDetail,
  submitNegotiationRequest,
} from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { code, money } from "../utils";

export default function PortalNegotiation() {
  const [data, setData] = useState({ quotation: null, lines: [] });
  const [requests, setRequests] = useState([]);
  const [comments, setComments] = useState({});
  const [counters, setCounters] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getQuotationDetail(1042), getNegotiationRequests(1042)]).then(
      ([d, r]) => {
        setData(d);
        setRequests(r);
        setLoading(false);
      }
    );
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

  const handleSubmit = async () => {
    setSubmitting(true);
    const newReqs = [];
    for (const line of data.lines) {
      if (comments[line.id] || counters[line.id]) {
        const payload = {
          quotation_id: data.quotation.id,
          quotation_line_id: line.id,
          customer_user_id: 41,
          message: comments[line.id] || `Requested ${counters[line.id]}% discount on ${line.product_id}`,
          counter_discount_pct: counters[line.id] ? Number(counters[line.id]) : null,
        };
        const res = await submitNegotiationRequest(payload);
        newReqs.push(res);
      }
    }
    setRequests((prev) => [...newReqs, ...prev]);
    setSubmitting(false);
    setComments({});
    setCounters({});
    setFeedback("Negotiation change requests submitted directly to the account sales team.");
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleConfirm = () => {
    setConfirmed(true);
    setFeedback("Quotation accepted & confirmed! Order routed for fulfillment processing.");
  };

  return (
    <DetailScreen
      title={`Commercial Quotation Review · ${code("Q", data.quotation.id)}`}
      subtitle={`Prepared for ${data.quotation.customer_name} · ${data.quotation.customer_tier} Tier Account`}
      actions={[
        {
          label: submitting ? "Submitting..." : "Submit Change Requests",
          onClick: handleSubmit,
        },
        {
          label: confirmed ? "Quotation Confirmed ✓" : "Confirm & Accept Quote",
          primary: true,
          variant: confirmed ? "success" : undefined,
          onClick: handleConfirm,
        },
      ]}
      banner={{
        title: "Customer Secure Commercial View:",
        body: "You can submit counter-discounts or special requirements per line item. Internal pricing calculations and margin rules are protected.",
      }}
    >
      {feedback && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-xs text-emerald-900 shadow-xs animate-fade-slide-in">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          <span className="font-semibold">{feedback}</span>
        </div>
      )}

      {/* Quotation Lines Card Grid */}
      <Panel
        title="Quotation Commercial Terms & Counter Proposals"
        right={<span className="text-xs text-slate-500">{data.lines.length} Line Items</span>}
      >
        <div className="space-y-4">
          {data.lines.map((line, idx) => (
            <div
              key={line.id}
              className={`rounded-xl border border-slate-200/90 bg-white p-4 shadow-xs transition-all duration-200 hover:border-indigo-300 hover:shadow-card animate-stagger-${
                idx + 1
              }`}
            >
              <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4 pb-3 border-b border-slate-100">
                <div>
                  <div className="text-xs font-bold text-slate-900 font-mono">{line.product_id}</div>
                  <div className="text-[11px] text-slate-400">{line.category}</div>
                </div>
                <div>
                  <div className="df-label">Quantity</div>
                  <div className="text-xs font-bold text-slate-800">{line.qty} units</div>
                </div>
                <div>
                  <div className="df-label">Unit Price</div>
                  <div className="font-mono text-xs font-bold text-slate-800">{money(line.unit_price)}</div>
                </div>
                <div>
                  <div className="df-label">Offered Discount</div>
                  <div className="font-mono text-xs font-bold text-indigo-700">{line.discount_pct}% Off</div>
                </div>
              </div>

              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <div className="sm:col-span-2">
                  <label className="df-label">Comment / Special Terms Request</label>
                  <textarea
                    aria-label={`Comment for ${line.product_id}`}
                    className="df-input min-h-[64px] text-xs"
                    placeholder="E.g. Requesting expedited shipping or volume adjustment..."
                    value={comments[line.id] || ""}
                    onChange={(e) =>
                      setComments((x) => ({ ...x, [line.id]: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="df-label">Counter Discount %</label>
                  <div className="relative">
                    <input
                      aria-label={`Counter discount for ${line.product_id}`}
                      className="df-input font-mono text-xs font-bold text-indigo-900"
                      type="number"
                      min="0"
                      max="100"
                      step="0.5"
                      placeholder="e.g. 21"
                      value={counters[line.id] || ""}
                      onChange={(e) =>
                        setCounters((x) => ({ ...x, [line.id]: e.target.value }))
                      }
                    />
                    <span className="absolute right-2.5 top-2 text-xs text-slate-400 font-mono pointer-events-none">
                      %
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">Proposed target discount</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Negotiation History / Messages */}
      <Panel
        title="Commercial Negotiation History"
        right={<span className="text-xs text-slate-500">{requests.length} Requests</span>}
      >
        <div className="space-y-2.5">
          {requests.map((r) => (
            <div
              key={r.id}
              className="flex items-start justify-between rounded-lg border border-slate-100 bg-slate-50/70 p-3 text-xs"
            >
              <div className="flex items-start gap-2.5">
                <MessageSquare className="h-4 w-4 text-indigo-600 mt-0.5 shrink-0" />
                <div>
                  <div className="font-semibold text-slate-800">
                    {r.message || "Quotation-level commercial request"}
                  </div>
                  {r.counter_discount_pct != null && (
                    <div className="mt-0.5 font-mono text-[11px] font-bold text-indigo-700">
                      Proposed Counter Discount: {r.counter_discount_pct}%
                    </div>
                  )}
                </div>
              </div>
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200 uppercase">
                {r.status}
              </span>
            </div>
          ))}
          {requests.length === 0 && (
            <div className="text-center py-6 text-xs text-slate-400">
              No previous negotiation requests for this quotation.
            </div>
          )}
        </div>
      </Panel>
    </DetailScreen>
  );
}

