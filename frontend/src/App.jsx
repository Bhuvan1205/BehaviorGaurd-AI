import { Routes, Route } from "react-router-dom";
import { PageLayout } from "./components/PageLayout"; // ✅ FIXED (named import)

import Dashboard from "./pages/Dashboard";
import RiskAnalyzer from "./pages/RiskAnalyzer";
import Monitoring from "./pages/Monitoring";
import Alerts from "./pages/Alerts";
import Reports from "./pages/Reports";
import Login from "./pages/Login";

export default function App() {
  return (
    <PageLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/risk-analyzer" element={<RiskAnalyzer />} />
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </PageLayout>
  );
}