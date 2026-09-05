import { useEffect, useState } from "react";
import { CheckCircle2, XCircle, UserCog, Clock } from "lucide-react";
import { getAdminUsers, approveUser, rejectUser } from "../../api/client";
import AdminNav from "../../components/AdminNav";
import Panel from "../../components/Panel";
import StatusBadge from "../../components/StatusBadge";
import Skeleton from "../../components/Skeleton";
import { useToast } from "../../context/ToastContext";
import { date } from "../../utils";

export default function AdminUsers() {
  const { toast } = useToast();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const load = () => getAdminUsers().then(setUsers);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const act = async (id, fn, label) => {
    setBusyId(id);
    try {
      await fn(id);
      toast(label, "success");
      await load();
    } catch (err) {
      toast(err.message || "Could not update user.", "error");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <Skeleton variant="card" count={3} />;

  const pending = users.filter((u) => u.status === "pending");
  const others = users.filter((u) => u.status !== "pending");

  return (
    <div className="space-y-6 animate-fade-slide-in">
      <AdminNav />
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">Internal User Sign-Up Approvals</h1>
        <p className="mt-1 text-xs text-slate-500">
          PDF A1/section 3 — new internal accounts (Sales Rep, Sales Manager, Finance) created via
          self-signup stay pending until an Admin approves them here. Admin accounts cannot self-signup.
        </p>
      </div>

      <Panel
        title="Pending Approval"
        right={<span className="text-xs font-bold text-amber-700">{pending.length} waiting</span>}
      >
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Requested Role</th>
                <th>Requested At</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {pending.map((u) => (
                <tr key={u.id}>
                  <td className="font-semibold text-xs text-slate-800">{u.name}</td>
                  <td className="font-mono text-xs text-slate-600">{u.email}</td>
                  <td>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold capitalize text-slate-700">
                      {u.role.replaceAll("_", " ")}
                    </span>
                  </td>
                  <td className="font-mono text-[11px] text-slate-400">{date(u.created_at)}</td>
                  <td>
                    <div className="flex justify-end gap-1.5">
                      <button
                        disabled={busyId === u.id}
                        onClick={() => act(u.id, approveUser, `${u.name} approved — they can now log in.`)}
                        className="df-btn-success !py-1 !px-2.5 text-[11px]"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                      </button>
                      <button
                        disabled={busyId === u.id}
                        onClick={() => act(u.id, rejectUser, `${u.name} rejected.`)}
                        className="df-btn-danger !py-1 !px-2.5 text-[11px]"
                      >
                        <XCircle className="h-3.5 w-3.5" /> Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!pending.length && (
                <tr>
                  <td colSpan={5} className="text-center text-xs text-slate-400 py-6">
                    <Clock className="h-4 w-4 mx-auto mb-1 text-slate-300" />
                    No pending sign-ups right now.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="All Internal Users" right={<UserCog className="h-4 w-4 text-slate-400" />}>
        <div className="overflow-x-auto">
          <table className="df-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {others.map((u) => (
                <tr key={u.id}>
                  <td className="font-semibold text-xs text-slate-800">{u.name}</td>
                  <td className="font-mono text-xs text-slate-600">{u.email}</td>
                  <td className="text-xs capitalize text-slate-700">{u.role.replaceAll("_", " ")}</td>
                  <td><StatusBadge value={u.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
