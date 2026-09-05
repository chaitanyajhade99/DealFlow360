import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { FileText, MessageSquare, User, ArrowLeft, ShieldCheck, Building } from "lucide-react";

const portal = [
  { label: "My Quotation", to: "/portal", icon: FileText },
  { label: "Messages", to: "/portal/messages", icon: MessageSquare },
  { label: "Account Profile", to: "/portal/profile", icon: User },
];

export default function PortalShell() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <header className="sticky top-0 z-40 border-b border-indigo-900/40 bg-[#1e293b] text-white shadow-sm backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate("/portal")}
              className="flex items-center gap-2 text-sm font-black tracking-tight text-white hover:opacity-90"
              aria-label="Customer Portal Home"
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500 text-white font-extrabold text-xs shadow-xs">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div className="flex flex-col text-left leading-tight">
                <span className="font-extrabold text-sm tracking-tight text-white">DealFlow360</span>
                <span className="text-[9px] font-semibold text-indigo-300 uppercase tracking-widest">
                  Customer Portal
                </span>
              </div>
            </button>

            <span className="h-5 w-px bg-slate-700 hidden sm:block" />

            <nav className="flex gap-1" aria-label="Portal Navigation">
              {portal.map(({ label, to, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/portal"}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all ${
                      isActive
                        ? "bg-white text-slate-900 shadow-xs scale-[1.02]"
                        : "text-slate-300 hover:bg-slate-800 hover:text-white"
                    }`
                  }
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <div className="hidden sm:flex items-center gap-1.5 text-slate-300">
              <Building className="h-3.5 w-3.5 text-indigo-400" />
              <span>Acme Corp</span>
            </div>
            <button
              onClick={() => navigate("/app")}
              className="flex items-center gap-1 rounded bg-slate-800 px-2.5 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
              aria-label="Switch to internal sales console"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Internal Ops</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6">
        <div key={location.pathname} className="animate-fade-slide-in">
          <Outlet />
        </div>
      </main>

      <footer className="mt-auto border-t border-slate-200/80 bg-white py-3 text-center text-[11px] text-slate-400">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 sm:px-6">
          <span>Acme Corp · Secure Customer Commercial Negotiation Portal</span>
          <span className="font-mono">DealFlow360</span>
        </div>
      </footer>
    </div>
  );
}

