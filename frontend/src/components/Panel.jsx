/* QuoteIt — Panel component */
export default function Panel({ title, children, className = "", right, noPad = false }) {
  return (
    <div className={`qit-panel overflow-hidden ${className}`}>
      {(title || right) && (
        <div className="qit-panel-header">
          {title && (
            <h2 className="qit-panel-title flex items-center gap-2">
              <span className="h-3 w-0.5 rounded-full bg-brand-500" aria-hidden="true" />
              {title}
            </h2>
          )}
          {right && <div className="text-xs text-ink-muted">{right}</div>}
        </div>
      )}
      <div className={noPad ? "" : "qit-panel-body"}>{children}</div>
    </div>
  );
}
