import { Navigate } from "react-router-dom";
import { useRole } from "../context/RoleContext";
import AppShell from "./AppShell";

export default function InternalRouteGuard() {
  const { role, isCustomer, internalUser } = useRole();

  if (isCustomer) {
    return <Navigate to="/portal" replace />;
  }
  if (!role || !internalUser) {
    return <Navigate to="/" replace />;
  }

  return <AppShell />;
}
