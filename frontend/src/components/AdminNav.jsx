import { NavLink } from "react-router-dom";

const links = [
  { label: "Products & Pricing", to: "/app/admin/products" },
  { label: "Discount Tiers & Approval Chains", to: "/app/admin/discount-config" },
  { label: "Warehouses", to: "/app/admin/warehouses" },
  { label: "Subscription Plans", to: "/app/admin/subscription-plans" },
  { label: "User Approvals", to: "/app/admin/users" },
  { label: "Customer Approvals", to: "/app/admin/customers" },
  { label: "Reporting", to: "/app/admin/reporting" },
];

export default function AdminNav() {
  return (
    <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-lg bg-slate-100/80 border border-slate-200/60 w-fit">
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            `rounded-md px-3 py-1.5 text-xs font-semibold transition-all duration-150 ${
              isActive
                ? "bg-white text-brand-700 shadow-xs border border-slate-200"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
            }`
          }
        >
          {l.label}
        </NavLink>
      ))}
    </div>
  );
}
