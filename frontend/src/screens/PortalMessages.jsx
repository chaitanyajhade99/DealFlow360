import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare } from "lucide-react";
import { getPortalNegotiations } from "../api/client";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { code, date } from "../utils";

export default function PortalMessages() {
  const navigate = useNavigate();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortalNegotiations()
      .then(setRequests)
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="space-y-4 animate-fade-slide-in">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-indigo-500" /> Messages
        </h1>
        <p className="mt-1 text-xs text-slate-500">Every change request and counter-discount your account has sent, across all quotations.</p>
      </div>

      <Panel title="Negotiation History">
        {loading ? (
          <Skeleton variant="tableRow" count={4} />
        ) : requests.length ? (
          <div className="divide-y divide-slate-100">
            {requests.map((r) => (
              <button
                key={r.id}
                onClick={() => navigate(`/portal/${r.quotation_id}`)}
                className="flex w-full items-start justify-between py-3 text-left hover:bg-slate-50/80 rounded-md px-2 -mx-2"
              >
                <div>
                  <div className="text-xs font-bold text-slate-800">
                    {code("Q", r.quotation_id)}
                    {r.counter_discount_pct != null && (
                      <span className="ml-2 font-mono text-brand-700">Counter: {r.counter_discount_pct}%</span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{r.message || "No message"}</div>
                  <div className="text-[10px] text-slate-400 mt-1">{date(r.created_at)}</div>
                </div>
                <StatusBadge value={r.status} />
              </button>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 py-6 text-center">No negotiation requests sent yet.</p>
        )}
      </Panel>
    </section>
  );
}
