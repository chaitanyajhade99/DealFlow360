import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from "lucide-react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "info", duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, toast: addToast, removeToast }}>
      {children}
      {/* Toast Render Container */}
      <div
        className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full"
        aria-live="polite"
      >
        {toasts.map((t) => {
          const isSuccess = t.type === "success";
          const isError = t.type === "error";
          const isWarning = t.type === "warning";
          
          let bg = "bg-slate-900 text-white border-slate-700";
          let Icon = Info;
          let iconColor = "text-sky-400";

          if (isSuccess) {
            bg = "bg-emerald-900 text-emerald-50 border-emerald-700";
            Icon = CheckCircle2;
            iconColor = "text-emerald-300";
          } else if (isError) {
            bg = "bg-rose-900 text-rose-50 border-rose-700";
            Icon = AlertCircle;
            iconColor = "text-rose-300";
          } else if (isWarning) {
            bg = "bg-amber-900 text-amber-50 border-amber-700";
            Icon = AlertTriangle;
            iconColor = "text-amber-300";
          }

          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex items-start gap-3 rounded-lg border p-3.5 shadow-lg backdrop-blur-md transition-all duration-200 animate-fade-slide-in ${bg}`}
              role="alert"
            >
              <Icon className={`h-5 w-5 shrink-0 mt-0.5 ${iconColor}`} />
              <div className="flex-1 text-xs leading-relaxed font-medium">
                {t.message}
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="shrink-0 text-white/60 hover:text-white transition-colors focus:outline-none"
                aria-label="Close notification"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    // Fallback if used outside provider
    return {
      addToast: (msg) => console.log("[Toast]", msg),
      toast: (msg) => console.log("[Toast]", msg),
      removeToast: () => {},
    };
  }
  return context;
}
