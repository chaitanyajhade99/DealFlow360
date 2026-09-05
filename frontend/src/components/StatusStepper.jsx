import { Check } from "lucide-react";

export default function StatusStepper({ steps, currentIndex = 0 }) {
  return (
    <nav aria-label="Progress" className="w-full overflow-x-auto py-2">
      <ol className="flex items-center min-w-[500px] w-full">
        {steps.map((step, index) => {
          const current = index === currentIndex;
          const complete = index < currentIndex;
          const isLast = index === steps.length - 1;

          return (
            <li
              key={step}
              className={`flex items-center ${!isLast ? "flex-1" : ""}`}
              aria-current={current ? "step" : undefined}
            >
              <div className="flex flex-col items-center group relative">
                <div
                  className={[
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all duration-300 shadow-xs",
                    current
                      ? "border-2 border-brand-600 bg-brand-600 text-white ring-4 ring-brand-100 shadow-sm scale-110"
                      : complete
                      ? "border-2 border-emerald-500 bg-emerald-500 text-white"
                      : "border-2 border-slate-300 bg-slate-50 text-slate-400",
                  ].join(" ")}
                  aria-label={`${step}: ${complete ? "Completed" : current ? "Current" : "Upcoming"}`}
                >
                  {complete ? (
                    <Check className="h-4 w-4 stroke-[2.5]" aria-hidden="true" />
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                <span
                  className={[
                    "mt-2 text-center text-xs font-semibold whitespace-nowrap transition-colors",
                    current
                      ? "text-brand-700 font-bold"
                      : complete
                      ? "text-slate-800"
                      : "text-slate-400 font-medium",
                  ].join(" ")}
                >
                  {step}
                </span>
              </div>

              {!isLast && (
                <div
                  className="mx-3 mb-6 h-1 flex-1 rounded-full bg-slate-200 overflow-hidden"
                  aria-hidden="true"
                >
                  <div
                    className={[
                      "h-full rounded-full transition-all duration-500 ease-out",
                      index < currentIndex ? "w-full bg-emerald-500" : "w-0 bg-transparent",
                    ].join(" ")}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

