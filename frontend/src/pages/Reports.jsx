import { useRealTime } from "../context/RealTimeContext";

export default function Reports() {
  const { userHistory, alerts } = useRealTime();

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">Reports</h1>

      <p>Total Events: {userHistory.length}</p>
      <p>Total Alerts: {alerts.length}</p>
    </div>
  );
}