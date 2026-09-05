import { AlertCircle, AlertTriangle, Info } from "lucide-react";

export default function DetailScreen({
  title,
  subtitle,
  actions = [],
  banner,
  sidePanel,
  children,
}) {
  return (
    <section className="space-y-4 animate-fade-slide-in">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {actions.map((item) => (
            <button
              key={item.label}
              onClick={item.onClick}
              className={
                item.variant === "danger"
                  ? "df-btn-danger"
                  : item.variant === "success"
                  ? "df-btn-success"
                  : item.primary
                  ? "df-btn-primary"
                  : "df-btn-secondary"
              }
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {banner && (
        <div
          className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-xs shadow-xs ${
            banner.tone === "danger"
              ? "border-red-300 bg-red-50 text-red-900"
              : "border-amber-300/80 bg-amber-50/90 text-amber-900"
          }`}
        >
          {banner.tone === "danger" ? (
            <AlertTriangle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" aria-hidden="true" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" aria-hidden="true" />
          )}
          <div>
            <span className="font-bold">{banner.title}</span>
            {banner.body && (
              <span
                className={`ml-1 ${banner.tone === "danger" ? "text-red-800" : "text-amber-800"}`}
              >
                {banner.body}
              </span>
            )}
          </div>
        </div>
      )}

      <div className={sidePanel ? "grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]" : "block"}>
        <div className="space-y-4 min-w-0">{children}</div>
        {sidePanel && <aside className="space-y-4 min-w-0">{sidePanel}</aside>}
      </div>
    </section>
  );
}

