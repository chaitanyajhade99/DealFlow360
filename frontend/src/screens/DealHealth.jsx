import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  Clock,
  Truck,
  ShieldAlert,
  ArrowRight,
  TrendingDown,
  Info,
} from "lucide-react";
import { getApprovals, getQuotations } from "../api/client";
import Panel from "../components/Panel";
import StatusBadge from "../components/StatusBadge";
import Skeleton from "../components/Skeleton";
import { code, date } from "../utils";

const RISK_COLORS = {
  HIGH: "#ef4444",
  MEDIUM: "#f59e0b",
  LOW: "#10b981",
};

export default function DealHealth() {
  const navigate = useNavigate();
  const [quotes, setQuotes] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getQuotations(), getApprovals()]).then(([q, a]) => {
      setQuotes(q);
      setApprovals(a);
      setLoading(false);
    });
  }, []);

  const stalled = quotes.filter((q) => q.status === "pending_approval");
  const anomalies = approvals.filter((a) => a.blended_risk === "HIGH");
  const slippage = quotes.filter((q) => q.status === "fulfillment");

  // Chart data sets
  const healthDistribution = [
    { name: "Stalled Deals", value: stalled.length || 1, color: "#f59e0b" },
    { name: "Discount Anomalies", value: anomalies.length || 1, color: "#ef4444" },
    { name: "Delivery In-Flight", value: slippage.length || 1, color: "#0ea5e9" },
    {
      name: "Healthy / Confirmed",
      value: quotes.filter((q) => q.status === "confirmed").length || 1,
      color: "#10b981",
    },
  ];

  const barData = [
    { category: "Stalled", count: stalled.length, fill: "#f59e0b" },
    { category: "High Risk", count: anomalies.length, fill: "#ef4444" },
    { category: "Fulfillment", count: slippage.length, fill: "#0ea5e9" },
    {
      category: "Confirmed",
      count: quotes.filter((q) => q.status === "confirmed").length,
      fill: "#10b981",
    },
  ];

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-slide-in">
        <Skeleton variant="title" className="w-1/2" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton variant="card" />
          <Skeleton variant="card" />
          <Skeleton variant="card" />
        </div>
      </div>
    );
  }

  return (
    <section className="space-y-5 animate-fade-slide-in">
      <div>
        <h1 className="text-xl font-black tracking-tight text-slate-900 flex items-center gap-2">
          Deal Health & Risk Anomaly Radar
          <span className="rounded-md bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700 border border-red-200">
            Anomaly Engine
          </span>
        </h1>
        <p className="mt-0.5 text-xs text-slate-500">
          Operational monitoring of stalled deals, discount guardrail breaches, and fulfillment delivery signals.
        </p>
      </div>

      {/* Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-amber-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px] text-amber-800">
              <Clock className="h-3.5 w-3.5 text-amber-500" />
              Stalled Governance
            </span>
          </div>
          <div className="mt-2 text-3xl font-black text-slate-900 font-mono">
            {stalled.length}
          </div>
          <div className="text-[11px] text-amber-700 mt-0.5">Awaiting management approvals</div>
        </div>

        <div className="rounded-xl border border-red-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px] text-red-800">
              <ShieldAlert className="h-3.5 w-3.5 text-red-500" />
              Discount Anomalies
            </span>
          </div>
          <div className="mt-2 text-3xl font-black text-slate-900 font-mono">
            {anomalies.length}
          </div>
          <div className="text-[11px] text-red-700 mt-0.5">HIGH blended margin breach</div>
        </div>

        <div className="rounded-xl border border-sky-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px] text-sky-800">
              <Truck className="h-3.5 w-3.5 text-sky-500" />
              Delivery In-Flight
            </span>
          </div>
          <div className="mt-2 text-3xl font-black text-slate-900 font-mono">
            {slippage.length}
          </div>
          <div className="text-[11px] text-sky-700 mt-0.5">Active warehouse routing</div>
        </div>
      </div>

      {/* Visual Analytics Grid: Donut + Bar Chart */}
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Pipeline Risk Health Breakdown">
          <div className="flex flex-col sm:flex-row items-center justify-around gap-4 h-48">
            <div className="h-44 w-44">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={healthDistribution}
                    innerRadius={45}
                    outerRadius={65}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {healthDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-1.5 text-xs">
              {healthDistribution.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-sm"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-slate-600 font-medium">{item.name}:</span>
                  <span className="font-bold text-slate-900 font-mono">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="Operational Stage Distribution">
          <div className="h-48 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="category" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      {/* Detailed Health Audit Table */}
      <Panel
        title="Live Deal Health Inspection Table"
        right={<span className="text-xs text-slate-500">{quotes.length} Total Pipeline Records</span>}
      >
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Quotation Ref</th>
                <th>Customer Account</th>
                <th>Pipeline Status</th>
                <th>Risk Signal</th>
                <th>Created Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {quotes.map((q, idx) => {
                const a = approvals.find((x) => x.quotation_id === q.id);
                return (
                  <tr key={q.id} className={`animate-stagger-${(idx % 5) + 1}`}>
                    <td className="font-mono text-xs font-bold text-brand-700">
                      {code("Q", q.id)}
                    </td>
                    <td>
                      <div className="font-bold text-xs text-slate-900">{q.customer_name}</div>
                      <div className="text-[11px] text-slate-400">{q.customer_tier} Tier</div>
                    </td>
                    <td>
                      <StatusBadge value={q.status} />
                    </td>
                    <td>{a ? <StatusBadge value={a.blended_risk} /> : <span className="text-xs text-slate-400">—</span>}</td>
                    <td className="text-xs text-slate-500 font-mono">{date(q.created_at)}</td>
                    <td>
                      <button
                        onClick={() => navigate(`/app/quotations/${q.id}`)}
                        className="df-btn-secondary py-1 px-2.5 text-[11px] gap-1"
                        aria-label={`Inspect deal ${code("Q", q.id)}`}
                      >
                        <span>Inspect</span>
                        <ArrowRight className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Contract Warning Banner */}
      <div className="flex items-start gap-3 rounded-lg border border-amber-300/80 bg-amber-50/90 px-4 py-3 text-xs text-amber-900 shadow-xs">
        <Info className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" aria-hidden="true" />
        <div>
          <span className="font-bold">Data Architecture Note:</span>
          <span className="ml-1 text-amber-800">
            The current Postgres schema does not contain explicit promised delivery dates or SLA timestamp fields, so "delivery slippage" is represented as an active fulfillment-state signal rather than a calculated calendar variance.
          </span>
        </div>
      </div>
    </section>
  );
}

