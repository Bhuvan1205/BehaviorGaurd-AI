import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { PageLayout } from "@/components/PageLayout";
import Dashboard from "@/pages/Dashboard";
import Monitoring from "@/pages/Monitoring";
import UserDetail from "@/pages/UserDetail";
import Alerts from "@/pages/Alerts";
import Reports from "@/pages/Reports";
import Login from "@/pages/Login";
import RiskAnalyzer from "@/pages/RiskAnalyzer";
import { RealTimeProvider } from "@/context/RealTimeContext";

function App() {
  return (
    <RealTimeProvider>
      <Router>
        <PageLayout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analyzer" element={<RiskAnalyzer />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/user/:id" element={<UserDetail />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/login" element={<Login />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </PageLayout>
      </Router>
    </RealTimeProvider>
  );
}

export default App;
