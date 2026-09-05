import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layers, ShieldCheck, ArrowRight, Lock, Mail, Sparkles, Info } from "lucide-react";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("jordan@dealflow360.test");
  const [role, setRole] = useState("sales_rep");

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white shadow-md">
          <Layers className="h-6 w-6 stroke-[2.5]" />
        </div>
        <h1 className="mt-4 text-2xl font-black tracking-tight text-slate-900">
          DealFlow360
        </h1>
        <p className="mt-1 text-xs text-slate-500 font-medium">
          End-to-End B2B Sales Operations & Governance Platform
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-md">
          <div className="border-b border-slate-100 pb-4 mb-5">
            <h2 className="text-base font-bold text-slate-900">Operator Authentication</h2>
            <p className="text-xs text-slate-500 mt-0.5">Select a workspace persona or login with credentials.</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="df-label">Email Address</label>
              <div className="relative">
                <Mail className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  aria-label="Email address"
                  className="df-input pl-9 text-xs"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="df-label">Password</label>
              <div className="relative">
                <Lock className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  aria-label="Password"
                  className="df-input pl-9 text-xs font-mono"
                  type="password"
                  defaultValue="mock-password"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => {
                  setEmail("jordan@dealflow360.test");
                  setRole("sales_rep");
                }}
                className={`rounded-lg border px-3 py-2 text-left transition-all ${
                  role === "sales_rep"
                    ? "border-brand-500 bg-brand-50/50 text-brand-900 ring-1 ring-brand-500"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                <div className="text-[11px] font-bold">Jordan Lee</div>
                <div className="text-[10px] text-slate-500">Sales Rep</div>
              </button>

              <button
                onClick={() => {
                  setEmail("maya@dealflow360.test");
                  setRole("sales_manager");
                }}
                className={`rounded-lg border px-3 py-2 text-left transition-all ${
                  role === "sales_manager"
                    ? "border-brand-500 bg-brand-50/50 text-brand-900 ring-1 ring-brand-500"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                <div className="text-[11px] font-bold">Maya Chen</div>
                <div className="text-[10px] text-slate-500">Sales Manager</div>
              </button>
            </div>

            <div className="pt-2 flex flex-col gap-2">
              <button
                onClick={() => navigate("/app")}
                className="df-btn-primary w-full py-2.5 text-xs font-bold gap-1.5"
                aria-label="Login to internal operations console"
              >
                <span>Enter Sales Operations Console</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>

              <button
                onClick={() => navigate("/portal")}
                className="df-btn-secondary w-full py-2.5 text-xs font-bold gap-1.5"
                aria-label="Open customer negotiation portal"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-indigo-600" />
                <span>Launch Customer Portal (Acme Corp)</span>
              </button>
            </div>
          </div>

          <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-[11px] text-amber-900">
            <Info className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <b>Hackathon Demo Mode:</b> Authentication is mock-only. Database schemas include placeholder password hashes ready for backend JWT wiring.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

