/* QuoteIt — Skeleton loading placeholders */
export default function Skeleton({ className = "", variant = "text", count = 1 }) {
  const styles = {
    text:     "h-4 w-full",
    title:    "h-6 w-2/5",
    card:     "h-32 w-full rounded-lg",
    tableRow: "h-11 w-full",
    circle:   "h-8 w-8 rounded-full",
    stat:     "h-20 w-full rounded-lg",
    button:   "h-9 w-24 rounded-md",
    badge:    "h-5 w-16 rounded-full",
  };

  const base = "qit-skeleton";

  if (count > 1) {
    return (
      <div className="space-y-2.5">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={`${base} ${styles[variant] || styles.text} ${className}`} />
        ))}
      </div>
    );
  }

  return <div className={`${base} ${styles[variant] || styles.text} ${className}`} />;
}
