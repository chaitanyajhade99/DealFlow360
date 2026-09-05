import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Layers, ShieldCheck, ArrowRight, Lock, Mail, Info, Loader2 } from "lucide-react";
import { useRole } from "../context/RoleContext";
import { useToast } from "../context/ToastContext";

const INTERNAL_PERSONAS = [
  { email: "j.rao@dealflow360.example", label: "J. Rao", role: "Sales Rep" },
  { email: "m.shah@dealflow360.example", label: "M. Shah", role: "Sales Manager" },
  { email: "k.iyer@dealflow360.example", label: "K. Iyer", role: "Finance" },
  { email: "admin@dealflow360.example", label: "Admin", role: "Admin" },
];

export default function Login() {
  const navigate = useNavigate();
  const { loginInternal, loginPortal } = useRole();
  const { toast } = useToast();
  const [mode, setMode] = useState("internal"); // "internal" | "portal"
  const [email, setEmail] = useState("j.rao@dealflow360.example");
  const [password, setPassword] = useState("password123");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (mode === "internal") {
        const data = await loginInternal(email, password);
        toast(`Welcome back, ${data.user.name}.`, "success");
        navigate("/app");
      } else {
        await loginPortal(email, password);
        toast("Portal access granted.", "success");
        navigate("/portal");
      }
    } catch (err) {
      toast(err.message || "Login failed. Check your credentials.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white shadow-md">
          <Layers className="h-6 w-6 stroke-[2.5]" />
        </div>
        <h1 className="mt-4 text-2xl font-black tracking-tight text-slate-900">DealFlow360</h1>
        <p className="mt-1 text-xs text-slate-500 font-medium">
          End-to-End B2B Sales Operations & Governance Platform
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-md">
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1 mb-5">
            <button
              type="button"
              onClick={() => {
                setMode("internal");
                setEmail("j.rao@dealflow360.example");
                setPassword("password123");
              }}
              className={`rounded-md py-2 text-xs font-bold transition-all ${
                mode === "internal" ? "bg-white text-brand-700 shadow-xs" : "text-slate-500"
              }`}
            >
              Internal Console
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("portal");
                setEmail("procurement@acme.example");
                setPassword("password123");
              }}
              className={`rounded-md py-2 text-xs font-bold transition-all ${
                mode === "portal" ? "bg-white text-indigo-700 shadow-xs" : "text-slate-500"
              }`}
            >
              Customer Portal
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="df-label">Email Address</label>
              <div className="relative">
                <Mail className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  aria-label="Email address"
                  className="df-input pl-9 text-xs"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
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
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
            </div>

            {mode === "internal" && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                {INTERNAL_PERSONAS.map((p) => (
                  <button
                    type="button"
                    key={p.email}
                    onClick={() => {
                      setEmail(p.email);
                      setPassword("password123");
                    }}
                    className={`rounded-lg border px-3 py-2 text-left transition-all ${
                      email === p.email
                        ? "border-brand-500 bg-brand-50/50 text-brand-900 ring-1 ring-brand-500"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <div className="text-[11px] font-bold">{p.label}</div>
                    <div className="text-[10px] text-slate-500">{p.role}</div>
                  </button>
                ))}
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={submitting}
                className={`w-full py-2.5 text-xs font-bold gap-1.5 ${
                  mode === "internal" ? "df-btn-primary" : "df-btn-secondary"
                }`}
                aria-label={mode === "internal" ? "Login to internal operations console" : "Login to customer portal"}
              >
                {submitting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : mode === "internal" ? (
                  <>
                    <span>Enter Sales Operations Console</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </>
                ) : (
                  <>
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>Open Customer Negotiation Portal</span>
                  </>
                )}
              </button>
            </div>
          </form>

          <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-sky-200 bg-sky-50/70 p-3 text-[11px] text-sky-900">
            <Info className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
            <div>
              <b>Live backend:</b> this form calls the real{" "}
              <code className="font-mono">POST /auth/login</code> /{" "}
              <code className="font-mono">POST /portal/login</code> endpoints and stores a
              real JWT. Password for every seeded account is <code className="font-mono">password123</code>.
            </div>
          </div>

          <p className="mt-4 text-center text-xs text-slate-500">
            New here?{" "}
            <Link to="/signup" className="font-bold text-brand-700 hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
