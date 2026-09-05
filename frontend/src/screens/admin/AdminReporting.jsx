import { useState } from "react";
import {
  BarChart3,
  TrendingUp,
  Clock,
  Sparkles,
  DollarSign,
  Filter,
  Layers,
  ArrowUpRight,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import Panel from "../../components/Panel";
import { money } from "../../utils";

export default function AdminReporting() {
  const [period, setPeriod] = useState("last_30_days");
  const [team, setTeam] = useState("all_teams");
  const [status, setStatus] = useState("all_statuses");
  const [product, setProduct] = useState("all_products");

  // Chart data
  const velocityData = [
    { day: "Mon", created: 6, approved: 5, avgHours: 3.2 },
    { day: "Tue", created: 8, approved: 7, avgHours: 2.8 },
    { day: "Wed", created: 12, approved: 10, avgHours: 4.1 },
    { day: "Thu", created: 9, approved: 8, avgHours: 2.4 },
    { day: "Fri", created: 14, approved: 12, avgHours: 3.6 },
    { day: "Sat", created: 3, approved: 3, avgHours: 1.5 },
    { day: "Sun", created: 2, approved: 2, avgHours: 1.2 },
  ];

  const categoryRevenue = [
    { name: "Hardware", value: 68400, color: "#0ea5e9" },
    { name: "Services", value: 24800, color: "#6366f1" },
    { name: "Subscriptions (ARR)", value: 42000, color: "#10b981" },
  ];

  return (
    <div className="space-y-6 animate-fade-slide-in">
      {/* Header */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Executive Governance & Ops Reporting
            </h1>
            <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-[10px] font-bold text-purple-800 border border-purple-200">
              Admin Exclusive
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Pipeline velocity, discount leakage metrics, and cross-territory approval telemetry.
          </p>
        </div>
      </div>

      {/* Filter Dropdowns Bar */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
        <div className="flex items-center gap-2 mb-3 text-xs font-bold text-slate-700">
          <Filter className="h-3.5 w-3.5 text-brand-600" />
          <span>Executive Filter Criteria</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="df-label">Reporting Period</label>
            <select
              className="df-input text-xs"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              aria-label="Filter by period"
            >
              <option value="last_7_days">Last 7 Days</option>
              <option value="last_30_days">Last 30 Days</option>
              <option value="q3_2026">Q3 2026 (Current Quarter)</option>
              <option value="ytd">Year to Date (2026)</option>
            </select>
          </div>

          <div>
            <label className="df-label">Sales Team / Territory</label>
            <select
              className="df-input text-xs"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
              aria-label="Filter by team"
            >
              <option value="all_teams">All Global Teams</option>
              <option value="north_america">Enterprise North America</option>
              <option value="emea">EMEA Strategic Accounts</option>
              <option value="apac">APAC Commercial Sales</option>
            </select>
          </div>

          <div>
            <label className="df-label">Approval Governance Status</label>
            <select
              className="df-input text-xs"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              aria-label="Filter by status"
            >
              <option value="all_statuses">All Approval Statuses</option>
              <option value="approved">Approved & Clean</option>
              <option value="pending_finance">Pending Finance Signoff</option>
              <option value="returned">Returned / Corrected</option>
            </select>
          </div>

          <div>
            <label className="df-label">Product / Service Line</label>
            <select
              className="df-input text-xs"
              value={product}
              onChange={(e) => setProduct(e.target.value)}
              aria-label="Filter by product"
            >
              <option value="all_products">All Catalog SKUs</option>
              <option value="hardware">Hardware (Laptops & Docks)</option>
              <option value="services">Care Plans & Warranty</option>
              <option value="subscriptions">Enterprise Subscriptions</option>
            </select>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span>Quotes Created</span>
            <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-bold text-sky-700">
              +18% MoM
            </span>
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">142</div>
          <div className="text-[11px] text-slate-400 mt-1">Total pipeline volume</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span>Avg Approval Turnaround</span>
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
              -42m Faster
            </span>
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">2.8 hrs</div>
          <div className="text-[11px] text-slate-400 mt-1">From submit to confirmation</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span>Top Upsold Product</span>
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          </div>
          <div className="mt-2 text-lg font-bold text-slate-900 truncate">USB-C Dock Pro</div>
          <div className="text-[11px] text-slate-400 mt-1">48% attach rate on laptops</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
            <span>Margin Protected</span>
            <ShieldCheck className="h-3.5 w-3.5 text-indigo-600" />
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">
            {money(38400)}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Saved via discount guardrails</div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Weekly Quote Pipeline Velocity & Signoff Throughput">
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={velocityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: "8px",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="created" name="Created" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                <Bar dataKey="approved" name="Approved" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Revenue Breakdown by Category & ARR Impact">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 h-64">
            <div className="h-full w-full sm:w-1/2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryRevenue}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {categoryRevenue.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val) => money(val)}
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="w-full sm:w-1/2 space-y-2.5">
              {categoryRevenue.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-3 w-3 rounded-sm shrink-0"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="font-semibold text-slate-700">{item.name}</span>
                  </div>
                  <span className="font-mono font-bold text-slate-900">{money(item.value)}</span>
                </div>
              ))}
              <div className="pt-2 border-t border-slate-100 flex justify-between text-xs font-bold text-slate-900">
                <span>Total Protected Revenue:</span>
                <span className="font-mono text-brand-700">{money(135200)}</span>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
