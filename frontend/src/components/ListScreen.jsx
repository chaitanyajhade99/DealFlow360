import { AlertCircle, Inbox, Search } from "lucide-react";
import { useState } from "react";

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
  searchable = false,
  searchPlaceholder = "Search…",
  children,
}) {
  const [search, setSearch] = useState("");

  const displayRows = searchable && search
    ? rows.filter((r) =>
        Object.values(r).some((v) =>
          String(v ?? "").toLowerCase().includes(search.toLowerCase())
        )
      )
    : rows;

  return (
    <section className="space-y-5 animate-fade-slide-in">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="qit-page-title">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {secondaryActions.map((item) => (
            <button key={item.label} onClick={item.onClick} className="qit-btn-secondary">
              {item.label}
            </button>
          ))}
          {action}
        </div>
      </div>

      {/* Filters + Search row */}
      {(filters.length > 0 || searchable) && (
        <div className="flex flex-wrap items-center gap-3 justify-between">
          {filters.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 p-1 rounded-lg border border-line bg-surface-muted w-fit">
              {filters.map((f) => {
                const isActive = activeFilter === f.value;
                return (
                  <button
                    key={f.value}
                    onClick={() => onFilterChange?.(f.value)}
                    className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-all duration-150 ${
                      isActive
                        ? "bg-surface text-ink shadow-xs border border-line"
                        : "text-ink-muted hover:text-ink hover:bg-surface/60"
                    }`}
                  >
                    {f.label}
                  </button>
                );
              })}
            </div>
          )}

          {searchable && (
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-ink-muted" />
              <input
                type="search"
                className="qit-input pl-8 py-1.5 text-xs w-52"
                placeholder={searchPlaceholder}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Search records"
              />
            </div>
          )}
        </div>
      )}

      {/* Banner */}
      {banner && (
        <div className="qit-alert qit-alert-warning">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" aria-hidden="true" />
          <div>
            <span className="font-semibold">{banner.title}</span>
            {banner.body && <span className="ml-1">{banner.body}</span>}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="qit-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="qit-table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col.key}>{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayRows.length ? (
                displayRows.map((row, idx) => (
                  <tr
                    key={row.id ?? JSON.stringify(row)}
                    className={`animate-stagger-${Math.min(idx + 1, 6)}`}
                  >
                    {columns.map((col) => (
                      <td key={col.key}>
                        {renderCell ? renderCell(row, col) : row[col.key]}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-14 text-center">
                    <div className="mx-auto flex max-w-xs flex-col items-center">
                      <div className="qit-empty-icon">
                        <Inbox className="h-6 w-6" aria-hidden="true" />
                      </div>
                      <p className="qit-empty-title">No records found</p>
                      <p className="qit-empty-body">
                        {search ? "No matches for your search." : "Try adjusting your filters."}
                      </p>
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
