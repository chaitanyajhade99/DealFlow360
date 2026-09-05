import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Layers, ArrowRight, ArrowLeft, Loader2, Info } from "lucide-react";
import { signupInternal } from "../api/client";
import { useRole } from "../context/RoleContext";
import { useToast } from "../context/ToastContext";

const INTERNAL_ROLES = [
  { value: "sales_rep", label: "Sales Rep" },
  { value: "sales_manager", label: "Sales Manager" },
  { value: "finance", label: "Finance" },
];

export default function Signup() {
  const navigate = useNavigate();
  const { signupPortal } = useRole();
  const { toast } = useToast();
  const [mode, setMode] = useState("internal"); // "internal" | "portal"
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const [internalForm, setInternalForm] = useState({
    name: "", email: "", password: "", role: "sales_rep",
  });
  const [portalForm, setPortalForm] = useState({
    companyName: "", email: "", password: "",
  });

  const handleInternalSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await signupInternal(internalForm);
      setDone(true);
      toast("Sign-up submitted — awaiting admin approval.", "success");
    } catch (err) {
      toast(err.message || "Sign-up failed.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePortalSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await signupPortal(portalForm);
      toast("Account created — welcome to the customer portal.", "success");
      navigate("/portal");
    } catch (err) {
      toast(err.message || "Sign-up failed.", "error");
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
        <h1 className="mt-4 text-2xl font-black tracking-tight text-slate-900">Create an Account</h1>
        <p className="mt-1 text-xs text-slate-500 font-medium">DealFlow360 sign-up</p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-md">
          <Link to="/" className="mb-4 inline-flex items-center gap-1 text-[11px] font-bold text-slate-500 hover:text-slate-800">
            <ArrowLeft className="h-3.5 w-3.5" /> Back to login
          </Link>

          <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1 mb-5">
            <button
              type="button"
              onClick={() => { setMode("internal"); setDone(false); }}
              className={`rounded-md py-2 text-xs font-bold transition-all ${mode === "internal" ? "bg-white text-brand-700 shadow-xs" : "text-slate-500"}`}
            >
              Internal Team
            </button>
            <button
              type="button"
              onClick={() => { setMode("portal"); setDone(false); }}
              className={`rounded-md py-2 text-xs font-bold transition-all ${mode === "portal" ? "bg-white text-indigo-700 shadow-xs" : "text-slate-500"}`}
            >
              Customer Portal
            </button>
          </div>

          {mode === "internal" && done && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-900">
              <b>Request submitted.</b> An Admin needs to approve your account before you can log
              in — check back soon, or ask your Admin to visit User Approvals.
            </div>
          )}

          {mode === "internal" && !done && (
            <form onSubmit={handleInternalSubmit} className="space-y-3.5">
              <div>
                <label className="df-label">Full Name</label>
                <input required className="df-input text-xs" value={internalForm.name}
                  onChange={(e) => setInternalForm({ ...internalForm, name: e.target.value })} />
              </div>
              <div>
                <label className="df-label">Work Email</label>
                <input required type="email" className="df-input text-xs" value={internalForm.email}
                  onChange={(e) => setInternalForm({ ...internalForm, email: e.target.value })} />
              </div>
              <div>
                <label className="df-label">Password</label>
                <input required type="password" className="df-input text-xs font-mono" value={internalForm.password}
                  onChange={(e) => setInternalForm({ ...internalForm, password: e.target.value })} />
              </div>
              <div>
                <label className="df-label">Role</label>
                <select className="df-input text-xs" value={internalForm.role}
                  onChange={(e) => setInternalForm({ ...internalForm, role: e.target.value })}>
                  {INTERNAL_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <button type="submit" disabled={submitting} className="w-full df-btn-primary py-2.5 text-xs font-bold gap-1.5">
                {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <><span>Request Access</span><ArrowRight className="h-3.5 w-3.5" /></>}
              </button>
              <div className="flex items-start gap-2.5 rounded-lg border border-sky-200 bg-sky-50/70 p-3 text-[11px] text-sky-900">
                <Info className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
                <div>Internal sign-ups need Admin approval before first login — this prevents anyone from granting themselves Sales Manager/Finance access.</div>
              </div>
            </form>
          )}

          {mode === "portal" && (
            <form onSubmit={handlePortalSubmit} className="space-y-3.5">
              <div>
                <label className="df-label">Company Name</label>
                <input required className="df-input text-xs" value={portalForm.companyName}
                  onChange={(e) => setPortalForm({ ...portalForm, companyName: e.target.value })}
                  placeholder="e.g. Acme Corp" />
              </div>
              <div>
                <label className="df-label">Email</label>
                <input required type="email" className="df-input text-xs" value={portalForm.email}
                  onChange={(e) => setPortalForm({ ...portalForm, email: e.target.value })} />
              </div>
              <div>
                <label className="df-label">Password</label>
                <input required type="password" className="df-input text-xs font-mono" value={portalForm.password}
                  onChange={(e) => setPortalForm({ ...portalForm, password: e.target.value })} />
              </div>
              <button type="submit" disabled={submitting} className="w-full df-btn-secondary py-2.5 text-xs font-bold gap-1.5">
                {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <span>Create Portal Account</span>}
              </button>
              <p className="text-[11px] text-slate-500">
                If your company already has open quotations with us, use the same company name
                to link your account to them. New accounts start at <b>Bronze</b> — your tier
                (and discount ceiling) rises automatically as more of your orders close, no
                need to pick one.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
