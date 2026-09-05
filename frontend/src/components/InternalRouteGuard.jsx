import { Navigate, Outlet } from "react-router-dom";
import { useRole, ROLES } from "../context/RoleContext";
import AppShell from "./AppShell";

export default function InternalRouteGuard() {
  const { role } = useRole();

  if (role === ROLES.CUSTOMER) {
    return <Navigate to="/portal/Q-1042" replace />;
  }

  return <AppShell />;
}
