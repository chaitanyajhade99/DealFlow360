import { Navigate } from "react-router-dom";
import { useRole } from "../context/RoleContext";
import PortalShell from "./PortalShell";

export default function PortalRouteGuard() {
  const { isCustomer } = useRole();

  if (!isCustomer) {
    return <Navigate to="/" replace />;
  }

  return <PortalShell />;
}
