import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { CheckCircle2, X } from "lucide-react";
import { getApprovalDetail, decideApproval, previewQuotationPdf } from "../api/client";
import DetailScreen from "../components/DetailScreen";
import Panel from "../components/Panel";
import StatusStepper from "../components/StatusStepper";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import { code, date, pct } from "../utils";

const RESOLVED_STAGES = ["confirmed", "rejected", "returned"];

const DEFAULT_NOTES = {
  approve: "Approved commercial terms.",
  return: "Returned for discount adjustment.",
  reject: "Commercial terms rejected.",
};

export default function ApprovalDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [data, setData] = useState({ approval: null, quotation: null, lines: [] });
  const [loading, setLoading] = useState(true);
  const [deciding, setDeciding] = useState(false);
  const [decisionFeedback, setDecisionFeedback] = useState(null);
  const [pendingAction, setPendingAction] = useState(null); // "approve" | "return" | "reject" | null
  const [noteDraft, setNoteDraft] = useState("");
  const [previewingPdf, setPreviewingPdf] = useState(false);

  const load = () => getApprovalDetail(id).then(setData);

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const resolved = RESOLVED_STAGES.includes(data.approval.stage);
  const current =
    data.approval.stage === "sales_manager"
      ? 1
      : data.approval.stage === "finance"
      ? 2
      : data.approval.stage === "confirmed"
      ? 3
      : 0;

  const handlePreviewPdf = async () => {
    setPreviewingPdf(true);
    try {
      await previewQuotationPdf(data.quotation.id);
    } catch (err) {
      toast(err.message || "Could not open PDF preview.", "error");
    } finally {
      setPreviewingPdf(false);
    }
  };

  const openDecisionModal = (action) => {
    setNoteDraft(DEFAULT_NOTES[action]);
    setPendingAction(action);
  };

  const handleDecision = async () => {
    const action = pendingAction;
    const note = noteDraft.trim() || DEFAULT_NOTES[action];
    setDeciding(true);
    try {
      const updated = await decideApproval(data.approval.id, action, note);
      setData((prev) => ({ ...prev, approval: updated }));
      setDecisionFeedback({ action, note, timestamp: new Date().toLocaleTimeString(), nextStage: updated.stage });
      setPendingAction(null);
      toast(
        updated.stage === "confirmed"
          ? "Approval chain cleared — quotation confirmed and invoiced."
          : updated.stage === "finance"
          ? "Escalated to Finance for the second approval step."
          : action === "return"
          ? "Returned to Sales Rep — quotation is editable again."
          : `Decision recorded: ${action}.`,
        "success"
      );
      load();
    } catch (err) {
      toast(err.message || "Could not record decision.", "error");
    } finally {
      setDeciding(false);
    }
  };

  const flaggedLines = data.approval.flagged_lines?.length
    ? data.approval.flagged_lines
    : data.lines.map((l) => ({
        line: l.product_id,
        discount_given_pct: l.discount_pct,
        limit_allowed_pct: l.category_limit_pct,
        over_by_pct: Number(l.discount_pct) - Number(l.category_limit_pct),
      }));

  return (
    <DetailScreen
      title={`Approval Review · ${code("A", data.approval.id)}`}
      subtitle={`Quotation ${code("Q", data.quotation.id)} · ${data.quotation.customer_name} · ${data.quotation.customer_tier} Tier`}
      actions={[
        {
          label: previewingPdf ? "Opening..." : "Preview Quotation PDF",
          onClick: handlePreviewPdf,
        },
        ...(resolved
          ? data.approval.stage === "returned"
            ? [
                {
                  label: "Edit Quotation",
                  primary: true,
                  onClick: () => navigate(`/app/quotations/${data.quotation.id}`),
                },
              ]
            : []
          : [
              { label: "Approve", variant: "success", onClick: () => openDecisionModal("approve") },
              { label: "Return for Revision", onClick: () => openDecisionModal("return") },
              { label: "Reject", variant: "danger", onClick: () => openDecisionModal("reject") },
            ]),
      ]}
      banner={{
        title: `${data.approval.blended_risk} Blended Risk Governance:`,
        body: resolved
          ? data.approval.stage === "returned"
            ? `This quotation was returned to the Sales Rep for revision — it's back in "draft" and editable. Use "Edit Quotation" above to adjust discounts and resubmit.`
            : `This approval is resolved — final stage: "${data.approval.stage}".`
          : `Current active stage is "${data.approval.stage.replaceAll(
              "_",
              " "
            )}", assigned to ${data.approval.assigned_to || "Unassigned"}. ${
              data.approval.blended_risk === "HIGH"
                ? "HIGH risk requires Sales Manager approval, then a second Finance approval."
                : ""
            }`,
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
              {flaggedLines.map((l, i) => {
                const variance = Number(l.over_by_pct);
                const isBreach = variance > 0;
                return (
                  <tr key={i}>
                    <td className="font-mono text-xs font-bold text-slate-900">{l.line}</td>
                    <td>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                        {l.category || "—"}
                      </span>
                    </td>
                    <td className="font-mono text-xs font-bold text-slate-800">{pct(l.discount_given_pct)}</td>
                    <td className="font-mono text-xs font-semibold text-slate-500">{pct(l.limit_allowed_pct)}</td>
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
              {!flaggedLines.length && (
                <tr>
                  <td colSpan={5} className="text-center text-xs text-slate-400 py-4">No lines were flagged — LOW risk, no policy breach.</td>
                </tr>
              )}
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

      {pendingAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h2 className="text-base font-bold text-slate-900 capitalize">{pendingAction} this approval</h2>
              <button onClick={() => setPendingAction(null)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
                <X className="h-4 w-4" />
              </button>
            </div>
            <label className="df-label">Note for the audit trail</label>
            <textarea
              className="df-input text-xs"
              rows={4}
              value={noteDraft}
              onChange={(e) => setNoteDraft(e.target.value)}
              placeholder="Explain your decision..."
              autoFocus
            />
            {pendingAction === "return" && (
              <p className="mt-2 text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                Returning sends this back to <b>draft</b> so the Sales Rep can edit line items and
                resubmit — you'll get an "Edit Quotation" shortcut here once it's returned.
              </p>
            )}
            <div className="mt-5 flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button type="button" onClick={() => setPendingAction(null)} className="df-btn-secondary">
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDecision}
                disabled={deciding}
                className={
                  pendingAction === "reject" ? "df-btn-danger" : pendingAction === "approve" ? "df-btn-success" : "df-btn-primary"
                }
              >
                {deciding ? "Saving..." : `Confirm ${pendingAction}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </DetailScreen>
  );
}

