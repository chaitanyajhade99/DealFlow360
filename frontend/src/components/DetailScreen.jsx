/* QuoteIt — DetailScreen layout wrapper */
import { AlertCircle, AlertTriangle, Info } from "lucide-react";

export default function DetailScreen({
  title,
  subtitle,
  badge,
  actions = [],
  banner,
  sidePanel,
  children,
}) {
  return (
    <section className="space-y-5 animate-fade-slide-in">

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="qit-page-title">{title}</h1>
            {badge && badge}
          </div>
          {subtitle && (
            <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>
          )}
        </div>

        {actions.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {actions.map((item) => (
              <button
                key={item.label}
                onClick={item.onClick}
                disabled={item.disabled}
                className={
                  item.variant === "danger"
                    ? "qit-btn-danger"
                    : item.variant === "success"
                    ? "qit-btn-success"
                    : item.variant === "warning"
                    ? "qit-btn-warning"
                    : item.primary
                    ? "qit-btn-primary"
                    : "qit-btn-secondary"
                }
              >
                {item.icon && <item.icon className="h-3.5 w-3.5" />}
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Banner ──────────────────────────────────────────────────── */}
      {banner && (
        <div
          className={`qit-alert ${
            banner.tone === "danger"
              ? "qit-alert-danger"
              : banner.tone === "success"
              ? "qit-alert-success"
              : banner.tone === "info"
              ? "qit-alert-info"
              : "qit-alert-warning"
          }`}
        >
          {banner.tone === "danger" ? (
            <AlertTriangle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" aria-hidden="true" />
          ) : banner.tone === "success" ? (
            <AlertCircle className="h-4 w-4 shrink-0 text-emerald-600 mt-0.5" aria-hidden="true" />
          ) : (
            <Info className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" aria-hidden="true" />
          )}
          <div>
            {banner.title && <span className="font-semibold">{banner.title} </span>}
            {banner.body && (
              <span>{banner.body}</span>
            )}
          </div>
        </div>
      )}

      {/* ── Content + optional side panel ───────────────────────────── */}
      <div className={sidePanel ? "grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]" : "block"}>
        <div className="space-y-5 min-w-0">{children}</div>
        {sidePanel && (
          <aside className="space-y-5 min-w-0">
            {sidePanel}
          </aside>
        )}
      </div>
    </section>
  );
}
