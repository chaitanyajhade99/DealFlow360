import { useEffect } from "react";
import { Navigate } from "react-router-dom";
import { useRole, ROLES } from "../context/RoleContext";
import { useToast } from "../context/ToastContext";

export default function AdminRouteGuard({ children }) {
  const { role } = useRole();
  const { toast } = useToast();

  const isAdmin = role === ROLES.ADMIN;

  useEffect(() => {
    if (!isAdmin) {
      toast("You don't have access to this page.", "warning");
    }
  }, [isAdmin, toast]);

  if (!isAdmin) {
    return <Navigate to="/app" replace />;
  }

  return children;
}
