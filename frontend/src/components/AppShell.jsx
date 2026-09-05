import { useState } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  CheckCircle2,
  Truck,
  Repeat,
  Receipt,
  Activity,
  BarChart3,
  LogOut,
  Menu,
  X,
  Layers,
  Sparkles,
} from "lucide-react";

const internal = [
  { label: "Dashboard", to: "/app", icon: LayoutDashboard },
  { label: "Quotations", to: "/app/quotations", icon: FileText },
  { label: "Approvals", to: "/app/approvals", icon: CheckCircle2 },
  { label: "Fulfillment", to: "/app/fulfillment", icon: Truck },
  { label: "Subscriptions", to: "/app/subscriptions", icon: Repeat },
  { label: "Invoices", to: "/app/invoices", icon: Receipt },
  { label: "Deal Health", to: "/app/deal-health", icon: Activity },
  { label: "Reports", to: "/app/reports", icon: BarChart3 },
];

export default function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <header className="sticky top-0 z-40 border-b border-brand-700/50 bg-[#0c5a96] text-white shadow-sm backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-2.5 sm:px-6">
          <div className="flex items-center gap-4 lg:gap-6">
            <button
              onClick={() => navigate("/app")}
              className="flex items-center gap-2 text-sm font-black tracking-tight text-white hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 focus:ring-white/30 rounded px-1"
              aria-label="DealFlow360 Home"
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white text-brand-700 font-extrabold text-xs shadow-xs">
                <Layers className="h-4 w-4 stroke-[2.5]" />
              </div>
              <div className="flex flex-col text-left leading-tight">
                <span className="font-extrabold text-sm tracking-tight text-white">DealFlow360</span>
                <span className="text-[9px] font-semibold text-white/70 uppercase tracking-widest">Ops Console</span>
              </div>
            </button>

            {/* Desktop / Tablet Nav */}
            <nav className="hidden md:flex items-center gap-1" aria-label="Main Navigation">
              {internal.map(({ label, to, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/app"}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold transition-all duration-150 ${
                      isActive
                        ? "bg-white text-brand-800 shadow-xs scale-[1.02]"
                        : "text-white/80 hover:bg-white/10 hover:text-white"
                    }`
                  }
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
          </div>

          {/* Right Header Area */}
          <div className="flex items-center gap-2.5 text-xs">
            <div className="hidden lg:flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 border border-white/15 text-[11px] text-white/90">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>Live Mocks</span>
            </div>

            <div className="hidden sm:flex flex-col text-right leading-none">
              <span className="font-semibold text-white text-xs">Jordan Lee</span>
              <span className="text-[10px] text-white/70">Sales Rep</span>
            </div>

            <button
              onClick={() => navigate("/")}
              className="flex items-center gap-1.5 rounded-md bg-white/10 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-white/20 transition-colors focus:outline-none focus:ring-2 focus:ring-white/40"
              aria-label="Log out of application"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">Logout</span>
            </button>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden rounded-md bg-white/10 p-1.5 text-white hover:bg-white/20 focus:outline-none"
              aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileOpen && (
          <nav className="md:hidden border-t border-white/10 bg-[#094777] px-4 py-3 space-y-1 animate-fade-slide-in">
            {internal.map(({ label, to, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/app"}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
                    isActive
                      ? "bg-white text-brand-800 font-bold"
                      : "text-white/80 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        )}
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        <div key={location.pathname} className="animate-fade-slide-in">
          <Outlet />
        </div>
      </main>

      <footer className="mt-auto border-t border-slate-200/80 bg-white py-3 text-center text-[11px] text-slate-400">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6">
          <span>DealFlow360 · B2B Sales Operations Platform</span>
          <span className="font-mono">v0.1.0-hackathon</span>
        </div>
      </footer>
    </div>
  );
}

