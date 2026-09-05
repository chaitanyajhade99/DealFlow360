import { useEffect, useState } from "react";
import { User } from "lucide-react";
import { getPortalMe } from "../api/client";
import Panel from "../components/Panel";
import Skeleton from "../components/Skeleton";
import { date } from "../utils";

export default function PortalProfile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortalMe()
      .then(setProfile)
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="space-y-4 animate-fade-slide-in">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <User className="h-5 w-5 text-indigo-500" /> Account Profile
        </h1>
        <p className="mt-1 text-xs text-slate-500">Your portal account details, from the real backend.</p>
      </div>

      <Panel title="Customer Account">
        {loading ? (
          <Skeleton variant="card" />
        ) : profile ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <div className="df-label">Company</div>
              <div className="font-semibold text-slate-900">{profile.customer.name}</div>
            </div>
            <div>
              <div className="df-label">Default Tier</div>
              <div className="font-semibold text-slate-900">{profile.customer.default_tier}</div>
            </div>
            <div>
              <div className="df-label">Contact Email</div>
              <div className="font-semibold text-slate-900">{profile.customer_user.email}</div>
            </div>
            <div>
              <div className="df-label">Auth Method</div>
              <div className="font-semibold text-slate-900 capitalize">{profile.customer_user.auth_method.replace("_", " ")}</div>
            </div>
            <div>
              <div className="df-label">Account Created</div>
              <div className="font-semibold text-slate-900">{date(profile.customer.created_at)}</div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-400">Could not load profile.</p>
        )}
      </Panel>
    </section>
  );
}
