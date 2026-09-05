import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import {
  Clock,
  FileText,
  AlertTriangle,
  ChevronRight,
  ArrowUpRight,
  Info,
  TrendingUp,
  Activity,
  Layers,
} from "lucide-react";
import { getApprovals, getQuotations } from "../api/client";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { code, date } from "../utils";

const pendingSparkData = [
  { v: 1 }, { v: 2 }, { v: 1 }, { v: 3 }, { v: 2 }, { v: pendingCountFallback(1) },
];
const openSparkData = [
  { v: 2 }, { v: 4 }, { v: 3 }, { v: 5 }, { v: 4 }, { v: 5 },
];
const atRiskSparkData = [
  { v: 0 }, { v: 1 }, { v: 2 }, { v: 1 }, { v: 2 }, { v: 2 },
];

function pendingCountFallback(c) {
  return c;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [quotations, setQuotations] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getQuotations(), getApprovals()])
      .then(([q, a]) => {
        setQuotations(q);
        setApprovals(a);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const pending = quotations.filter((q) => q.status === "pending_approval");
  const open = quotations.filter((q) =>
    ["draft", "pending_approval", "approved"].includes(q.status)
  );
  const atRisk = approvals.filter((a) => a.blended_risk !== "LOW");

  return (
    <section className="space-y-5 animate-fade-slide-in">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-xl font-black tracking-tight text-slate-900 flex items-center gap-2">
            Sales Dashboard
            <span className="rounded-md bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700 border border-brand-200/60">
              Overview
            </span>
          </h1>
          <p className="mt-0.5 text-xs text-slate-500">
            Real-time pipeline health, pending governance queues, and deal risk analytics.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate("/app/quotations/1042")}
            className="df-btn-primary"
            aria-label="Create new quotation"
          >
            <span>+ New Quotation</span>
          </button>
        </div>
      </div>

      {/* 3 Metric Stat Cards with Recharts Sparklines */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Pending Approvals Card */}
        <div
          onClick={() => navigate("/app/approvals")}
          className="group cursor-pointer rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover"
          role="button"
          tabIndex={0}
          aria-label="View pending approvals"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
              <Clock className="h-3.5 w-3.5 text-amber-500" aria-hidden="true" />
              Pending Approvals
            </span>
            <ArrowUpRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-brand-600 transition-colors" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                {loading ? <Skeleton variant="title" className="w-12" /> : pending.length}
              </div>
              <p className="mt-0.5 text-[11px] text-amber-700 font-medium">Awaiting manager/finance</p>
            </div>
            <div className="h-10 w-24">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={pendingSparkData}>
                  <defs>
                    <linearGradient id="amberGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="v"
                    stroke="#d97706"
                    strokeWidth={2}
                    fill="url(#amberGrad)"
                    dot={false}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Open Quotations Card */}
        <div
          onClick={() => navigate("/app/quotations")}
          className="group cursor-pointer rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover"
          role="button"
          tabIndex={0}
          aria-label="View open quotations"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
              <FileText className="h-3.5 w-3.5 text-brand-500" aria-hidden="true" />
              Open Quotations
            </span>
            <ArrowUpRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-brand-600 transition-colors" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                {loading ? <Skeleton variant="title" className="w-12" /> : open.length}
              </div>
              <p className="mt-0.5 text-[11px] text-brand-700 font-medium">Draft, review & active</p>
            </div>
            <div className="h-10 w-24">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={openSparkData}>
                  <defs>
                    <linearGradient id="brandGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0f75c6" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#0f75c6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="v"
                    stroke="#0f75c6"
                    strokeWidth={2}
                    fill="url(#brandGrad)"
                    dot={false}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* At-Risk Deals Card */}
        <div
          onClick={() => navigate("/app/deal-health")}
          className="group cursor-pointer rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-red-300 hover:shadow-card-hover sm:col-span-2 lg:col-span-1"
          role="button"
          tabIndex={0}
          aria-label="View at-risk deals"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
              <AlertTriangle className="h-3.5 w-3.5 text-red-500" aria-hidden="true" />
              At-Risk Deals
            </span>
            <ArrowUpRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-red-600 transition-colors" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                {loading ? <Skeleton variant="title" className="w-12" /> : atRisk.length}
              </div>
              <p className="mt-0.5 text-[11px] text-red-700 font-medium">Medium / High blended risk</p>
            </div>
            <div className="h-10 w-24">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={atRiskSparkData}>
                  <defs>
                    <linearGradient id="redGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ef4444" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#ef4444" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="v"
                    stroke="#dc2626"
                    strokeWidth={2}
                    fill="url(#redGrad)"
                    dot={false}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Activity & Queue Columns */}
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          title="Recent Quotation Activity"
          right={
            <button
              onClick={() => navigate("/app/quotations")}
              className="text-xs font-semibold text-brand-600 hover:text-brand-800 transition-colors"
            >
              View all →
            </button>
          }
        >
          {loading ? (
            <Skeleton variant="tableRow" count={4} />
          ) : (
            <div className="divide-y divide-slate-100">
              {quotations.slice(0, 4).map((q, i) => (
                <button
                  key={q.id}
                  onClick={() => navigate(`/app/quotations/${q.id}`)}
                  className={`flex w-full items-center justify-between py-3 text-left transition-colors hover:bg-slate-50/80 rounded-md px-2 -mx-2 animate-stagger-${i + 1}`}
                  aria-label={`Open quotation ${code("Q", q.id)} for ${q.customer_name}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700 font-mono font-bold text-xs">
                      {code("Q", q.id).slice(-2)}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-800">
                        {code("Q", q.id)} · <span className="font-semibold text-slate-700">{q.customer_name}</span>
                      </div>
                      <div className="text-[11px] text-slate-400">Created {date(q.created_at)} · {q.customer_tier} Tier</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={q.status} />
                    <ChevronRight className="h-4 w-4 text-slate-300" aria-hidden="true" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel
          title="Pending Approval Queue"
          right={
            <button
              onClick={() => navigate("/app/approvals")}
              className="text-xs font-semibold text-brand-600 hover:text-brand-800 transition-colors"
            >
              View queue →
            </button>
          }
        >
          {loading ? (
            <Skeleton variant="tableRow" count={3} />
          ) : (
            <div className="divide-y divide-slate-100">
              {approvals.slice(0, 4).map((a, i) => (
                <button
                  key={a.id}
                  onClick={() => navigate(`/app/approvals/${a.id}`)}
                  className={`flex w-full items-center justify-between py-3 text-left transition-colors hover:bg-slate-50/80 rounded-md px-2 -mx-2 animate-stagger-${i + 1}`}
                  aria-label={`Open approval ${code("A", a.id)} for quotation ${code("Q", a.quotation_id)}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 text-amber-700 font-mono font-bold text-xs">
                      {code("A", a.id).slice(-2)}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-800">
                        {code("A", a.id)} · <span className="capitalize">{a.stage.replaceAll("_", " ")}</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Quote {code("Q", a.quotation_id)} · Assigned: {a.assigned_to || "Unassigned"}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={a.blended_risk} />
                    <ChevronRight className="h-4 w-4 text-slate-300" aria-hidden="true" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Workflow Banner */}
      <div className="flex items-start gap-3 rounded-lg border border-amber-300/80 bg-amber-50/90 px-4 py-3 text-xs text-amber-900 shadow-xs">
        <Info className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" aria-hidden="true" />
        <div>
          <span className="font-bold">End-to-End Pipeline Workflow:</span>
          <span className="ml-1 text-amber-800">
            Quotes move from <b>Sales Dashboard</b> → <b>Quotations</b> → <b>Approval</b> → <b>Fulfillment</b> → <b>Invoices & Payments</b>. Customer negotiations occur in the separate portal shell.
          </span>
        </div>
      </div>
    </section>
  );
}

