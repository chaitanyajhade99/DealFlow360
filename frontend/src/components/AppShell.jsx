import { useState } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard, FileText, CheckCircle2, Truck, Repeat, Receipt,
  Activity, BarChart3, LogOut, Menu, X, PackageX, Settings,
  Users, Tag, Warehouse, Package, ChevronRight, Zap, Bell,
  ArrowUpRight,
} from "lucide-react";
import { useRole, ROLE_DETAILS } from "../context/RoleContext";

/* ─── Navigation structure ─────────────────────────────────────────── */
const NAV_GROUPS = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", to: "/app", icon: LayoutDashboard, end: true }],
  },
  {
    label: "Sales",
    items: [
      { label: "Quotations",  to: "/app/quotations",  icon: FileText },
      { label: "Approvals",   to: "/app/approvals",   icon: CheckCircle2 },
    ],
    roles: null, // all roles
  },
  {
    label: "Operations",
    items: [
      { label: "Fulfillment", to: "/app/fulfillment", icon: Truck },
      { label: "Backorders",  to: "/app/backorders",  icon: PackageX, financeOnly: true },
    ],
  },
  {
    label: "Billing",
    items: [
      { label: "Subscriptions", to: "/app/subscriptions", icon: Repeat },
      { label: "Invoices",      to: "/app/invoices",      icon: Receipt, financeOnly: true },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { label: "Deal Health", to: "/app/deal-health", icon: Activity },
      { label: "Reports",     to: "/app/reports",     icon: BarChart3 },
    ],
  },
];

const ADMIN_GROUP = {
  label: "Administration",
  items: [
    { label: "Products",       to: "/app/admin/products",           icon: Package },
    { label: "Discount Rules", to: "/app/admin/discount-config",    icon: Tag },
    { label: "Warehouses",     to: "/app/admin/warehouses",         icon: Warehouse },
    { label: "Subscr. Plans",  to: "/app/admin/subscription-plans", icon: Repeat },
    { label: "Users & Roles",  to: "/app/admin/users",              icon: Users },
    { label: "Customers",      to: "/app/admin/customers",          icon: Users },
  ],
};

/* ─── Role initials for avatar ─────────────────────────────────────── */
function initials(name = "") {
  return name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0]?.toUpperCase() || "")
    .join("");
}

/* ─── Sidebar nav item ─────────────────────────────────────────────── */
function SideItem({ item, collapsed, onClick }) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onClick}
      className={({ isActive }) =>
        `qit-nav-item ${isActive ? "active" : ""}`
      }
      title={collapsed ? item.label : undefined}
    >
      <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  );
}

/* ─── Main AppShell ─────────────────────────────────────────────────── */
export default function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { internalUser, isAdmin, isFinance, logout } = useRole();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const canSeeFinanceOnly = isFinance || isAdmin;

  // Filter items based on role
  const filteredGroups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.financeOnly || canSeeFinanceOnly),
  })).filter((group) => group.items.length > 0);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const sidebarW = collapsed ? "64px" : "240px";

  return (
    <div className="flex min-h-screen bg-canvas font-sans">

      {/* ── Mobile overlay ──────────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside
        style={{ width: collapsed ? "64px" : "240px" }}
        className={`
          fixed top-0 left-0 h-full z-50 flex flex-col
          bg-[#0f172a] border-r border-white/[0.06]
          transition-[width] duration-200 ease-in-out overflow-hidden
          ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
        aria-label="Main navigation sidebar"
      >
        {/* Logo */}
        <div
          className="flex items-center gap-3 px-4 h-14 border-b border-white/[0.06] shrink-0 cursor-pointer"
          onClick={() => navigate("/app")}
          role="button"
          tabIndex={0}
          aria-label="QuoteIt home"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600 shrink-0">
            <Zap className="h-4 w-4 text-white" aria-hidden="true" />
          </div>
          {!collapsed && (
            <div className="flex flex-col leading-tight">
              <span className="text-[14px] font-bold text-white tracking-tight">QuoteIt</span>
              <span className="text-[9px] font-semibold text-white/40 uppercase tracking-widest">
                Sales Intelligence
              </span>
            </div>
          )}
        </div>

        {/* Nav groups */}
        <nav className="flex-1 overflow-y-auto overflow-x-hidden py-3 space-y-0.5 px-2">
          {filteredGroups.map((group) => (
            <div key={group.label}>
              {!collapsed && (
                <p className="qit-nav-section">{group.label}</p>
              )}
              {collapsed && <div className="pt-3 pb-1 border-t border-white/[0.06] mx-1 first:border-t-0 first:pt-0" />}
              {group.items.map((item) => (
                <SideItem
                  key={item.to}
                  item={item}
                  collapsed={collapsed}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </div>
          ))}

          {/* Admin group */}
          {isAdmin && (
            <div>
              {!collapsed && <p className="qit-nav-section">Administration</p>}
              {collapsed && <div className="pt-3 pb-1 border-t border-white/[0.06] mx-1" />}
              {ADMIN_GROUP.items.map((item) => (
                <SideItem
                  key={item.to}
                  item={item}
                  collapsed={collapsed}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </div>
          )}
        </nav>

        {/* User profile at bottom */}
        <div className="shrink-0 border-t border-white/[0.06] p-3">
          {!collapsed ? (
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white text-[11px] font-bold">
                {initials(internalUser?.name)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-semibold text-white truncate">
                  {internalUser?.name || "User"}
                </div>
                <div className="text-[10px] text-white/50 truncate">
                  {ROLE_DETAILS[internalUser?.role]?.label || internalUser?.role}
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="rounded p-1.5 text-white/40 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="Log out"
                title="Log out"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={handleLogout}
              className="flex w-full items-center justify-center rounded p-2 text-white/40 hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Log out"
              title="Log out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="hidden lg:flex items-center justify-center shrink-0 h-9 w-full border-t border-white/[0.06] text-white/30 hover:text-white hover:bg-white/05 transition-colors"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <ChevronRight
            className={`h-3.5 w-3.5 transition-transform duration-200 ${collapsed ? "" : "rotate-180"}`}
          />
        </button>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <div
        className="flex flex-1 flex-col min-h-screen transition-[margin] duration-200"
        style={{ marginLeft: collapsed ? "64px" : "240px" }}
      >
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex h-14 items-center border-b border-line bg-surface px-6 gap-4">
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen((v) => !v)}
            className="lg:hidden qit-btn-ghost qit-btn-icon rounded"
            aria-label="Open navigation"
          >
            <Menu className="h-4 w-4" />
          </button>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Live indicator */}
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live Backend
          </div>

          {/* User info */}
          <div className="hidden sm:flex items-center gap-2">
            <div className="text-right">
              <div className="text-[12px] font-semibold text-ink leading-none">
                {internalUser?.name || "—"}
              </div>
              <div className="text-[10px] text-ink-muted mt-0.5">
                {ROLE_DETAILS[internalUser?.role]?.label || internalUser?.role}
              </div>
            </div>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-white text-[11px] font-bold">
              {initials(internalUser?.name)}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6">
          <div key={location.pathname} className="animate-fade-slide-in max-w-[1440px] mx-auto">
            <Outlet />
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-line bg-surface py-3 px-6">
          <div className="flex items-center justify-between max-w-[1440px] mx-auto text-[11px] text-ink-muted">
            <span>QuoteIt · From Quote to Closure, Intelligently.</span>
            <span className="font-mono">v1.0.0-hackathon</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
