import { AlertCircle, Info, Inbox } from "lucide-react";

export default function ListScreen({
  title,
  subtitle,
  filters = [],
  activeFilter,
  onFilterChange,
  columns,
  rows,
  renderCell,
  banner,
  action,
  secondaryActions = [],
  children,
}) {
  return (
    <section className="space-y-4 animate-fade-slide-in">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {secondaryActions.map((item) => (
            <button key={item.label} onClick={item.onClick} className="df-btn-secondary">
              {item.label}
            </button>
          ))}
          {action}
        </div>
      </div>

      {filters.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-lg bg-slate-100/80 border border-slate-200/60 w-fit">
          {filters.map((filter) => {
            const isActive = activeFilter === filter.value;
            return (
              <button
                key={filter.value}
                onClick={() => onFilterChange?.(filter.value)}
                className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-all duration-150 ${
                  isActive
                    ? "bg-white text-brand-700 shadow-xs border border-slate-200"
                    : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
                }`}
              >
                {filter.label}
              </button>
            );
          })}
        </div>
      )}

      {banner && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-300/80 bg-amber-50/90 px-4 py-3 text-xs text-amber-900 shadow-xs">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" aria-hidden="true" />
          <div>
            <span className="font-bold">{banner.title}</span>
            {banner.body && <span className="ml-1 text-amber-800">{banner.body}</span>}
          </div>
        </div>
      )}

      <div className="df-panel overflow-hidden border border-slate-200/80 bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.key}>{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length ? (
                rows.map((row, idx) => {
                  const staggerClass =
                    idx === 0
                      ? "animate-stagger-1"
                      : idx === 1
                      ? "animate-stagger-2"
                      : idx === 2
                      ? "animate-stagger-3"
                      : idx === 3
                      ? "animate-stagger-4"
                      : idx === 4
                      ? "animate-stagger-5"
                      : "animate-stagger-6";

                  return (
                    <tr key={row.id ?? JSON.stringify(row)} className={staggerClass}>
                      {columns.map((column) => (
                        <td key={column.key}>
                          {renderCell ? renderCell(row, column) : row[column.key]}
                        </td>
                      ))}
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={columns.length} className="px-3 py-12 text-center">
                    <div className="mx-auto flex max-w-xs flex-col items-center justify-center text-slate-400">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 mb-2">
                        <Inbox className="h-5 w-5 text-slate-400" aria-hidden="true" />
                      </div>
                      <p className="text-xs font-semibold text-slate-600">No records found</p>
                      <p className="mt-0.5 text-[11px] text-slate-400">Try adjusting your filters to find records.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {children}
    </section>
  );
}

