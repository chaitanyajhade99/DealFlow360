import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, UserCheck, ShieldCheck } from "lucide-react";
import { getApprovals } from "../api/client";
import ListScreen from "../components/ListScreen";
import StatusBadge from "../components/StatusBadge";
import { code, date } from "../utils";

export default function ApprovalsList() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    getApprovals().then(setRows);
  }, []);

  const filtered = useMemo(
    () => (filter === "all" ? rows : rows.filter((r) => r.blended_risk === filter)),
    [rows, filter]
  );

  return (
    <ListScreen
      title="Approvals Queue (List)"
      subtitle="Audit, route, and decide governance on commercial quotes breaching tier boundaries."
      filters={[
        { value: "all", label: "All Risks" },
        { value: "LOW", label: "Low Risk" },
        { value: "MEDIUM", label: "Medium Risk" },
        { value: "HIGH", label: "High Risk" },
      ]}
      activeFilter={filter}
      onFilterChange={setFilter}
      banner={{
        title: "Risk-based multi-tier approval matrix active:",
        body: "HIGH risk blended quotes require dual signoff: Sales Manager followed by Finance Controller.",
      }}
      columns={[
        { key: "id", label: "Approval ID" },
        { key: "quotation_id", label: "Quotation Ref" },
        { key: "blended_risk", label: "Risk Level" },
        { key: "stage", label: "Current Stage" },
        { key: "assigned_to", label: "Reviewer Assigned" },
      ]}
      rows={filtered}
      renderCell={(row, col) =>
        col.key === "id" ? (
          <button
            className="font-bold text-brand-700 hover:text-brand-900 hover:underline flex items-center gap-1 group font-mono text-xs"
            onClick={() => navigate(`/app/approvals/${row.id}`)}
            aria-label={`Open approval ${code("A", row.id)}`}
          >
            <span>{code("A", row.id)}</span>
            <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        ) : col.key === "quotation_id" ? (
          <button
            onClick={() => navigate(`/app/quotations/${row.quotation_id}`)}
            className="font-mono text-xs font-semibold text-slate-700 hover:text-brand-700 hover:underline"
          >
            {code("Q", row.quotation_id)}
          </button>
        ) : col.key === "blended_risk" ? (
          <StatusBadge value={row.blended_risk} />
        ) : col.key === "stage" ? (
          <span className="capitalize font-semibold text-slate-700">
            {row.stage.replaceAll("_", " ")}
          </span>
        ) : row.assigned_to ? (
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold text-slate-700">
              {row.assigned_to
                .split(" ")
                .map((n) => n[0])
                .join("")}
            </div>
            <span className="text-xs font-medium text-slate-800">{row.assigned_to}</span>
          </div>
        ) : (
          <span className="text-xs text-slate-400 italic">Unassigned</span>
        )
      }
    />
  );
}

