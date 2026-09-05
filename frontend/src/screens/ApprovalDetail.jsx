import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  CheckCircle2,
  XCircle,
  RotateCcw,
  ShieldAlert,
  History,
  User,
  ArrowRight,
} from "lucide-react";
import { getApprovalDetail, decideApproval } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import StatusStepper from "../components/StatusStepper";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { code, date, money, pct } from "../utils";

export default function ApprovalDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState({ approval: null, quotation: null, lines: [] });
  const [loading, setLoading] = useState(true);
  const [decisionFeedback, setDecisionFeedback] = useState(null);

  useEffect(() => {
    getApprovalDetail(id).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [id]);

  if (loading || !data.approval) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const current =
    data.approval.stage === "sales_manager"
      ? 1
      : data.approval.stage === "finance"
      ? 2
      : data.approval.stage === "confirmed"
      ? 3
      : 0;

  const handleDecision = async (action, note) => {
    const res = await decideApproval(data.approval.id, action, note);
    setDecisionFeedback({ action, note, timestamp: new Date().toLocaleTimeString() });
  };

  return (
    <DetailScreen
      title={`Approval Review · ${code("A", data.approval.id)}`}
      subtitle={`Quotation ${code("Q", data.quotation.id)} · ${data.quotation.customer_name} · ${data.quotation.customer_tier} Tier`}
      actions={[
        {
          label: "Approve Quotation",
          variant: "success",
          onClick: () => handleDecision("approve", "Approved commercial terms."),
        },
        {
          label: "Return for Revision",
          onClick: () => handleDecision("return", "Returned for discount adjustment."),
        },
        {
          label: "Reject Quote",
          variant: "danger",
          onClick: () => handleDecision("reject", "Commercial terms rejected."),
        },
      ]}
      banner={{
        title: `${data.approval.blended_risk} Blended Risk Governance:`,
        body: `Current active stage is "${data.approval.stage.replaceAll(
          "_",
          " "
        )}", assigned to ${data.approval.assigned_to || "Unassigned"}.`,
      }}
    >
      {decisionFeedback && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs text-emerald-900 animate-fade-slide-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>
              Decision <b>{decisionFeedback.action.toUpperCase()}</b> recorded locally at{" "}
              {decisionFeedback.timestamp}.
            </span>
          </div>
          <button
            onClick={() => setDecisionFeedback(null)}
            className="text-[11px] font-bold text-emerald-700 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Stage Stepper Tracker */}
      <Panel title="Multi-Stage Approval Pipeline">
        <div className="py-2">
          <StatusStepper
            steps={["Submitted", "Sales Manager", "Finance", "Confirmed"]}
            currentIndex={current}
          />
        </div>
      </Panel>

      {/* Why This Quote Was Flagged */}
      <Panel
        title="Flagged Line Items & Policy Breach Breakdown"
        right={
          <span className="text-xs text-slate-500">
            Quotation {code("Q", data.quotation.id)}
          </span>
        }
      >
        <div className="grid gap-3 sm:grid-cols-3 mb-4">
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="df-label">Customer Tier</div>
            <div className="text-xs font-bold text-slate-800">{data.quotation.customer_tier} Tier</div>
          </div>
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="df-label">Assigned Reviewer</div>
            <div className="text-xs font-bold text-slate-800">{data.approval.assigned_to || "None"}</div>
          </div>
          <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="df-label">Blended Risk</div>
            <div><StatusBadge value={data.approval.blended_risk} /></div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Category</th>
                <th>Requested Discount</th>
                <th>Tier Limit</th>
                <th>Policy Variance</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l) => {
                const variance = Number(l.discount_pct) - Number(l.category_limit_pct);
                const isBreach = variance > 0;
                return (
                  <tr key={l.id}>
                    <td className="font-mono text-xs font-bold text-slate-900">{l.product_id}</td>
                    <td>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                        {l.category}
                      </span>
                    </td>
                    <td className="font-mono text-xs font-bold text-slate-800">{pct(l.discount_pct)}</td>
                    <td className="font-mono text-xs font-semibold text-slate-500">{pct(l.category_limit_pct)}</td>
                    <td>
                      {isBreach ? (
                        <span className="inline-flex items-center gap-1 rounded bg-red-50 px-2 py-0.5 text-[11px] font-bold text-red-700 border border-red-200">
                          +{pct(variance)} OVER LIMIT
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700 border border-emerald-200">
                          Within Limit
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Audit Trail */}
      <Panel title="Governance Audit Trail & Timestamped History">
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Reviewer</th>
                <th>Action Taken</th>
                <th>Internal Note</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {data.approval.history.map((h, i) => (
                <tr key={i} className={`animate-stagger-${i + 1}`}>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-700">
                        {h.user
                          .split(" ")
                          .map((n) => n[0])
                          .join("")}
                      </div>
                      <span className="font-semibold text-xs text-slate-800">{h.user}</span>
                    </div>
                  </td>
                  <td>
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider text-slate-700 border border-slate-200">
                      {h.action}
                    </span>
                  </td>
                  <td className="text-xs text-slate-600">{h.note || "—"}</td>
                  <td className="font-mono text-[11px] text-slate-400">{date(h.at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </DetailScreen>
  );
}

