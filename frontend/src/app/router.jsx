import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { AboutPage } from "../pages/AboutPage";
import { AlertsPage } from "../pages/AlertsPage";
import { DashboardPage } from "../pages/DashboardPage";
import { UploadPage } from "../pages/UploadPage";
import { SignInPage } from "../pages/SignInPage";
import { UserDetailPage } from "../pages/UserDetailPage";
import { EmailSecurityDashboard } from "../pages/EmailSecurityDashboard";
import { ProtectedRoute } from "../components/ProtectedRoute";

export function AppRouter() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/signin" element={<SignInPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/email-security" element={<EmailSecurityDashboard />} />
            <Route path="/user-analytics" element={<UserDetailPage />} />
            <Route path="/user/:id" element={<UserDetailPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  );
}
