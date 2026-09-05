import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import { ToastProvider } from "./context/ToastContext";
import { RoleProvider } from "./context/RoleContext";
import InternalRouteGuard from "./components/InternalRouteGuard";
import AdminRouteGuard from "./components/AdminRouteGuard";
import PortalRouteGuard from "./components/PortalRouteGuard";
import Login from "./screens/Login";
import Dashboard from "./screens/Dashboard";
import QuotationsList from "./screens/QuotationsList";
import QuotationDetail from "./screens/QuotationDetail";
import ApprovalsList from "./screens/ApprovalsList";
import ApprovalDetail from "./screens/ApprovalDetail";
import FulfillmentList from "./screens/FulfillmentList";
import FulfillmentDetail from "./screens/FulfillmentDetail";
import SubscriptionsList from "./screens/SubscriptionsList";
import BillingDetail from "./screens/BillingDetail";
import PortalNegotiation from "./screens/PortalNegotiation";
import InvoicesList from "./screens/InvoicesList";
import InvoiceDetail from "./screens/InvoiceDetail";
import DealHealth from "./screens/DealHealth";
import Reports from "./screens/Reports";
import PortalMessages from "./screens/PortalMessages";
import PortalProfile from "./screens/PortalProfile";
import AdminProducts from "./screens/admin/AdminProducts";
import AdminDiscountConfig from "./screens/admin/AdminDiscountConfig";
import AdminReporting from "./screens/admin/AdminReporting";
import AdminWarehouses from "./screens/admin/AdminWarehouses";
import AdminSubscriptionPlans from "./screens/admin/AdminSubscriptionPlans";
import AdminUsers from "./screens/admin/AdminUsers";
import Signup from "./screens/Signup";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Protected Internal Routes */}
        <Route path="/app" element={<InternalRouteGuard />}>
          <Route index element={<Dashboard />} />
          <Route path="quotations" element={<QuotationsList />} />
          <Route path="quotations/:id" element={<QuotationDetail />} />
          <Route path="approvals" element={<ApprovalsList />} />
          <Route path="approvals/:id" element={<ApprovalDetail />} />
          <Route path="fulfillment" element={<FulfillmentList />} />
          <Route path="fulfillment/:id" element={<FulfillmentDetail />} />
          <Route path="subscriptions" element={<SubscriptionsList />} />
          <Route path="billing/:id" element={<BillingDetail />} />
          <Route path="invoices" element={<InvoicesList />} />
          <Route path="invoices/:id" element={<InvoiceDetail />} />
          <Route path="deal-health" element={<DealHealth />} />
          <Route path="reports" element={<Reports />} />
          
          {/* Admin Restricted Routes */}
          <Route
            path="admin/products"
            element={
              <AdminRouteGuard>
                <AdminProducts />
              </AdminRouteGuard>
            }
          />
          <Route
            path="admin/discount-config"
            element={
              <AdminRouteGuard>
                <AdminDiscountConfig />
              </AdminRouteGuard>
            }
          />
          <Route
            path="admin/reporting"
            element={
              <AdminRouteGuard>
                <AdminReporting />
              </AdminRouteGuard>
            }
          />
          <Route
            path="admin/warehouses"
            element={
              <AdminRouteGuard>
                <AdminWarehouses />
              </AdminRouteGuard>
            }
          />
          <Route
            path="admin/subscription-plans"
            element={
              <AdminRouteGuard>
                <AdminSubscriptionPlans />
              </AdminRouteGuard>
            }
          />
          <Route
            path="admin/users"
            element={
              <AdminRouteGuard>
                <AdminUsers />
              </AdminRouteGuard>
            }
          />
        </Route>

        {/* Customer Portal Standalone Routes */}
        <Route path="/portal" element={<PortalRouteGuard />}>
          <Route index element={<PortalNegotiation />} />
          <Route path=":quotationId" element={<PortalNegotiation />} />
          <Route path="messages" element={<PortalMessages />} />
          <Route path="profile" element={<PortalProfile />} />
        </Route>

        {/* Aliases & Fallbacks */}
        <Route path="/dashboard" element={<Navigate to="/app" replace />} />
        <Route path="/admin/products" element={<Navigate to="/app/admin/products" replace />} />
        <Route path="/admin/discount-config" element={<Navigate to="/app/admin/discount-config" replace />} />
        <Route path="/admin/reporting" element={<Navigate to="/app/admin/reporting" replace />} />
        <Route path="/billing" element={<Navigate to="/app/subscriptions" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ToastProvider>
      <RoleProvider>
        <App />
      </RoleProvider>
    </ToastProvider>
  </React.StrictMode>
);
