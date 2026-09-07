import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Zap, ArrowRight, Lock, Mail, Info, Loader2, ShieldCheck, Eye, EyeOff,
} from "lucide-react";
import { useRole } from "../context/RoleContext";
import { useToast } from "../context/ToastContext";

const INTERNAL_PERSONAS = [
  { email: "j.rao@dealflow360.example",    label: "J. Rao",    role: "Sales Rep",      color: "bg-sky-500" },
  { email: "m.shah@dealflow360.example",   label: "M. Shah",   role: "Sales Manager",  color: "bg-indigo-500" },
  { email: "k.iyer@dealflow360.example",   label: "K. Iyer",   role: "Finance",        color: "bg-emerald-500" },
  { email: "admin@dealflow360.example",    label: "Admin",     role: "Admin",          color: "bg-violet-500" },
];

function initials(label) {
  return label.split(" ").map((w) => w[0]).join("").toUpperCase();
}

export default function Login() {
  const navigate = useNavigate();
  const { loginInternal, loginPortal } = useRole();
  const { toast } = useToast();
  const [mode, setMode] = useState("internal");
  const [email, setEmail] = useState("j.rao@dealflow360.example");
  const [password, setPassword] = useState("password123");
  const [showPw, setShowPw] = useState(false);
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
    <div className="min-h-screen flex font-sans bg-canvas">

      {/* ── Left brand panel ─────────────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-[480px] xl:w-[520px] flex-col justify-between
                      bg-[#0f172a] p-10 relative overflow-hidden shrink-0">
        {/* Background pattern */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 right-0 w-80 h-80 rounded-full bg-brand-600/10 blur-3xl -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-96 h-96 rounded-full bg-brand-600/5  blur-3xl  translate-y-1/2 -translate-x-1/3" />
        </div>

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-lg font-bold text-white tracking-tight">QuoteIt</div>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-white/40">
              Sales Intelligence Platform
            </div>
          </div>
        </div>

        {/* Hero copy */}
        <div className="relative">
          <h1 className="text-3xl font-bold text-white leading-tight tracking-tight">
            From Quote to Closure,{" "}
            <span className="text-brand-400">Intelligently.</span>
          </h1>
          <p className="mt-4 text-sm text-white/60 leading-relaxed max-w-sm">
            AI-powered discount governance, automatic approval routing, multi-warehouse fulfillment,
            and real-time deal health — all in one platform.
          </p>

          {/* Feature bullets */}
          <ul className="mt-8 space-y-3">
            {[
              "Intelligent discount governance & approval chains",
              "AI upsell / cross-sell recommendations",
              "Multi-warehouse fulfillment orchestration",
              "Customer negotiation portal",
              "Deal health monitoring & anomaly detection",
            ].map((f) => (
              <li key={f} className="flex items-center gap-2.5 text-[12px] text-white/70">
                <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-brand-600/30 text-brand-400 text-[9px]">✓</span>
                {f}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative text-[11px] text-white/25 font-medium">
          Intelligent B2B Sales Operations · Hackathon Demo
        </div>
      </div>

      {/* ── Right form panel ─────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col justify-center items-center p-6 sm:p-10">

        {/* Mobile logo */}
        <div className="flex lg:hidden items-center gap-2 mb-8">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div className="text-lg font-bold text-ink tracking-tight">QuoteIt</div>
        </div>

        <div className="w-full max-w-[400px]">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-ink tracking-tight">Sign in</h2>
            <p className="mt-1 text-sm text-ink-muted">
              {mode === "internal"
                ? "Access the QuoteIt Sales Operations Console"
                : "Access your Customer Negotiation Portal"}
            </p>
          </div>

          {/* Mode toggle */}
          <div className="flex rounded-lg border border-line bg-surface-muted p-1 mb-6 gap-1">
            {[
              { id: "internal", label: "Internal Console" },
              { id: "portal",   label: "Customer Portal"  },
            ].map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => {
                  setMode(id);
                  setEmail(id === "internal" ? "j.rao@dealflow360.example" : "procurement@acme.example");
                  setPassword("password123");
                }}
                className={`flex-1 rounded-md py-2 text-xs font-semibold transition-all duration-150 ${
                  mode === id
                    ? "bg-surface shadow-xs text-ink"
                    : "text-ink-muted hover:text-ink"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label className="qit-label" htmlFor="email">Email address</label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-ink-muted" />
                <input
                  id="email"
                  type="email"
                  aria-label="Email address"
                  className="qit-input pl-9 text-sm"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="qit-label" htmlFor="password">Password</label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-ink-muted" />
                <input
                  id="password"
                  type={showPw ? "text" : "password"}
                  aria-label="Password"
                  className="qit-input pl-9 pr-9 font-mono text-sm"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute right-3 top-2.5 text-ink-muted hover:text-ink transition-colors"
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Persona quick-select (internal only) */}
            {mode === "internal" && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted mb-2">
                  Quick select demo persona
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {INTERNAL_PERSONAS.map((p) => (
                    <button
                      type="button"
                      key={p.email}
                      onClick={() => { setEmail(p.email); setPassword("password123"); }}
                      className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs
                        transition-all duration-150 ${
                        email === p.email
                          ? "border-brand-400 bg-brand-50 text-brand-900 ring-1 ring-brand-400"
                          : "border-line bg-surface text-ink-secondary hover:border-line-strong hover:bg-surface-muted"
                      }`}
                    >
                      <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${p.color} text-white text-[9px] font-bold`}>
                        {initials(p.label)}
                      </div>
                      <div>
                        <div className="font-semibold text-[11px]">{p.label}</div>
                        <div className="text-[10px] text-ink-muted">{p.role}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting}
              className="qit-btn-primary qit-btn-lg w-full mt-2"
              aria-label={mode === "internal" ? "Sign in to the sales console" : "Sign in to the customer portal"}
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : mode === "internal" ? (
                <>Enter Sales Console <ArrowRight className="h-4 w-4" /></>
              ) : (
                <><ShieldCheck className="h-4 w-4" /> Open Customer Portal</>
              )}
            </button>
          </form>

          {/* Info note */}
          <div className="mt-5 qit-alert qit-alert-info">
            <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
            <div className="text-[11px]">
              <b>Live backend:</b> Calls real{" "}
              <code className="font-mono bg-blue-100 px-1 rounded">POST /auth/login</code>{" "}
              endpoint. Password for all demo accounts:{" "}
              <code className="font-mono bg-blue-100 px-1 rounded">password123</code>
            </div>
          </div>

          <p className="mt-5 text-center text-xs text-ink-muted">
            New company?{" "}
            <Link to="/signup" className="font-semibold text-brand-600 hover:underline">
              Request portal access
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
