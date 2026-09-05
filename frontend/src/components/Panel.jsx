export default function Panel({ title, children, className = "", right }) {
  return (
    <div className={`df-panel overflow-hidden border border-slate-200/90 bg-white shadow-xs hover:shadow-sm transition-shadow duration-200 ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/40 px-4 py-3 sm:px-5">
          {title && (
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
              <span className="h-2 w-2 rounded-sm bg-brand-600/80" aria-hidden="true" />
              {title}
            </h2>
          )}
          {right && <div className="text-xs font-medium text-slate-600">{right}</div>}
        </div>
      )}
      <div className="p-4 sm:p-5">{children}</div>
    </div>
  );
}

