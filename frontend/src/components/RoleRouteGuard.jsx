import { useEffect } from "react";
import { Navigate } from "react-router-dom";
import { useRole } from "../context/RoleContext";
import { useToast } from "../context/ToastContext";

// Generic per-role route gate, for screens restricted to specific internal
// roles by PS convention (e.g. Invoices -> Finance/Admin) but not exclusive
// to Admin (that case stays AdminRouteGuard). Mirrors the corresponding
// backend read-access gate so a role that can't reach the API can't reach
// the screen either -- bouncing here is a UX courtesy, not the real
// enforcement (the API's own role check is what actually protects the data).
export default function RoleRouteGuard({ allow, children }) {
  const { role } = useRole();
  const { toast } = useToast();

  const allowed = allow.includes(role);

  useEffect(() => {
    if (!allowed) {
      toast("You don't have access to this page.", "warning");
    }
  }, [allowed, toast]);

  if (!allowed) {
    return <Navigate to="/app" replace />;
  }

  return children;
}
