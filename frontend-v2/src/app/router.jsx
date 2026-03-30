import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { AboutPage } from "../pages/AboutPage";
import { AlertsPage } from "../pages/AlertsPage";
import { DashboardPage } from "../pages/DashboardPage";
import { LiveFeedPage } from "../pages/LiveFeedPage";
import { MonitoringPage } from "../pages/MonitoringPage";
import { SignInPage } from "../pages/SignInPage";
import { UserDetailPage } from "../pages/UserDetailPage";
import { ProtectedRoute } from "../components/ProtectedRoute";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/signin" element={<SignInPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/live" element={<LiveFeedPage />} />
            <Route path="/monitor" element={<MonitoringPage />} />
            <Route path="/user-analytics" element={<UserDetailPage />} />
            <Route path="/user/:id" element={<UserDetailPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
