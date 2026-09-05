import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  getInternalSession,
  getCustomerSession,
  loginInternal as apiLoginInternal,
  loginPortal as apiLoginPortal,
  signupPortal as apiSignupPortal,
  logoutInternal,
  logoutPortal,
} from "../api/client";

export const ROLES = {
  SALES_REP: "sales_rep",
  SALES_MANAGER: "sales_manager",
  FINANCE: "finance",
  CUSTOMER: "customer",
  ADMIN: "admin",
};

export const ROLE_DETAILS = {
  sales_rep: {
    label: "Sales Rep",
    badge: "bg-sky-500/20 text-sky-200 border-sky-400/40",
    badgeLight: "bg-sky-50 text-sky-700 border-sky-200",
    desc: "Build quotes, discounts, request approvals & customer followups",
  },
  sales_manager: {
    label: "Sales Manager",
    badge: "bg-indigo-500/20 text-indigo-200 border-indigo-400/40",
    badgeLight: "bg-indigo-50 text-indigo-700 border-indigo-200",
    desc: "Stage-1 approvals, pipeline oversight, escalation radar",
  },
  finance: {
    label: "Finance",
    badge: "bg-emerald-500/20 text-emerald-200 border-emerald-400/40",
    badgeLight: "bg-emerald-50 text-emerald-700 border-emerald-200",
    desc: "Stage-2 finance approvals, record payments, manage billing",
  },
  admin: {
    label: "Admin",
    badge: "bg-purple-500/20 text-purple-200 border-purple-400/40",
    badgeLight: "bg-purple-50 text-purple-700 border-purple-200",
    desc: "Full governance, catalog admin, discount rules & executive reporting",
  },
  customer: {
    label: "Customer",
    badge: "bg-amber-500/20 text-amber-200 border-amber-400/40",
    badgeLight: "bg-amber-50 text-amber-700 border-amber-200",
    desc: "External portal to review quotes, negotiate & approve agreements",
  },
};

const RoleContext = createContext(null);

export function RoleProvider({ children }) {
  const [internalSession, setInternalSessionState] = useState(() => getInternalSession());
  const [customerSession, setCustomerSessionState] = useState(() => getCustomerSession());

  // Pick up session changes made by client.js (e.g. a 401 clearing the
  // session, or another tab logging out) by re-reading on focus.
  useEffect(() => {
    const sync = () => {
      setInternalSessionState(getInternalSession());
      setCustomerSessionState(getCustomerSession());
    };
    window.addEventListener("focus", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("focus", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const role = internalSession?.user?.role || (customerSession ? ROLES.CUSTOMER : null);

  const loginInternal = useCallback(async (email, password) => {
    const data = await apiLoginInternal(email, password);
    setInternalSessionState(getInternalSession());
    return data;
  }, []);

  const loginPortal = useCallback(async (email, password) => {
    const data = await apiLoginPortal(email, password);
    setCustomerSessionState(getCustomerSession());
    return data;
  }, []);

  const signupPortal = useCallback(async (form) => {
    const data = await apiSignupPortal(form);
    setCustomerSessionState(getCustomerSession());
    return data;
  }, []);

  const logout = useCallback(() => {
    logoutInternal();
    logoutPortal();
    setInternalSessionState(null);
    setCustomerSessionState(null);
  }, []);

  return (
    <RoleContext.Provider
      value={{
        role,
        roles: ROLES,
        roleDetails: ROLE_DETAILS,
        internalUser: internalSession?.user || null,
        customerProfile: customerSession?.profile || null,
        isAuthenticated: Boolean(internalSession || customerSession),
        isSalesRep: role === ROLES.SALES_REP,
        isSalesManager: role === ROLES.SALES_MANAGER,
        isFinance: role === ROLES.FINANCE,
        isCustomer: role === ROLES.CUSTOMER,
        isAdmin: role === ROLES.ADMIN,
        loginInternal,
        loginPortal,
        signupPortal,
        logout,
      }}
    >
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error("useRole must be used within a RoleProvider");
  }
  return context;
}
