export default function Skeleton({ className = "", variant = "text", count = 1 }) {
  const base = "animate-pulse bg-slate-200/80 rounded";
  const styles = {
    text: "h-4 w-full",
    title: "h-6 w-1/3",
    card: "h-28 w-full rounded-xl",
    tableRow: "h-12 w-full",
    circle: "h-8 w-8 rounded-full",
  };

  if (count > 1) {
    return (
      <div className="space-y-2">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={`${base} ${styles[variant] || styles.text} ${className}`} />
        ))}
      </div>
    );
  }

  return <div className={`${base} ${styles[variant] || styles.text} ${className}`} />;
}
