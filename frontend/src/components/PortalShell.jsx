import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  FileText, MessageSquare, User, ShieldCheck,
  Building, LogOut, Receipt, Zap, Home,
} from "lucide-react";
import { useRole } from "../context/RoleContext";

const PORTAL_LINKS = [
  { label: "My Quotations", to: "/portal",          icon: FileText,      end: true },
  { label: "Billing",       to: "/portal/billing",  icon: Receipt              },
  { label: "Messages",      to: "/portal/messages", icon: MessageSquare        },
  { label: "Account",       to: "/portal/profile",  icon: User                 },
];

export default function PortalShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { customerProfile, logout } = useRole();
  const customerName = customerProfile?.customer?.name || "Your Account";

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-canvas font-sans flex flex-col">

      {/* ── Top header bar ─────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-[#0f172a] border-b border-white/[0.06] shadow-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">

          {/* Logo + Nav */}
          <div className="flex items-center gap-5">
            <button
              onClick={() => navigate("/portal")}
              className="flex items-center gap-2.5 shrink-0"
              aria-label="QuoteIt Customer Portal Home"
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600">
                <Zap className="h-4 w-4 text-white" aria-hidden="true" />
              </div>
              <div className="flex flex-col text-left leading-tight">
                <span className="text-sm font-bold text-white tracking-tight">QuoteIt</span>
                <span className="text-[9px] font-semibold text-white/40 uppercase tracking-widest">
                  Customer Portal
                </span>
              </div>
            </button>

            <span className="hidden sm:block h-5 w-px bg-white/10" aria-hidden="true" />

            <nav className="hidden sm:flex items-center gap-0.5" aria-label="Portal Navigation">
              {PORTAL_LINKS.map(({ label, to, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all duration-100 ${
                      isActive
                        ? "bg-white/10 text-white"
                        : "text-white/60 hover:text-white hover:bg-white/[0.06]"
                    }`
                  }
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {/* Company name */}
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-white/60">
              <Building className="h-3.5 w-3.5 text-brand-400" aria-hidden="true" />
              <span className="font-medium">{customerName}</span>
            </div>

            {/* Logout */}
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.04]
                         px-3 py-1.5 text-xs font-semibold text-white/60
                         hover:bg-white/10 hover:text-white transition-colors"
              aria-label="Log out of the customer portal"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">Log Out</span>
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        <div className="sm:hidden border-t border-white/[0.06] px-4 py-2">
          <nav className="flex items-center gap-1" aria-label="Portal Mobile Navigation">
            {PORTAL_LINKS.map(({ label, to, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex flex-1 flex-col items-center gap-0.5 rounded-md py-1.5 text-[10px] font-semibold transition-all ${
                    isActive ? "bg-white/10 text-white" : "text-white/50 hover:text-white"
                  }`
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label.split(" ")[0]}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6">
        <div key={location.pathname} className="animate-fade-slide-in">
          <Outlet />
        </div>
      </main>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="mt-auto border-t border-line bg-surface py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 sm:px-6 text-[11px] text-ink-muted">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" aria-hidden="true" />
            <span>Secure encrypted commercial portal</span>
          </div>
          <span className="font-semibold text-ink">QuoteIt</span>
        </div>
      </footer>
    </div>
  );
}
