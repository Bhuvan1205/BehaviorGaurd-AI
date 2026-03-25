import { useState } from "react";
import { sendEvent, mapToBackendFormat } from "../services/api";
import { useRealTime } from "../context/RealTimeContext";

export default function Dashboard() {
  const { userHistory, addEventToHistory } = useRealTime();

  const [risk, setRisk] = useState(0);
  const [alerts, setAlerts] = useState([]);

  async function handleEvent() {
    try {
      const frontendData = {
        userId: "user_123",
        logons: 1,
        devices: 1,
      };

      const payload = mapToBackendFormat(frontendData, userHistory);

      const response = await sendEvent(payload);

      addEventToHistory(payload.event);

      setRisk(response.aggregated_risk);

      if (response.alert.alert) {
        setAlerts((prev) => [
          {
            message: `Anomaly detected for ${response.alert.user_id}`,
            time: "just now",
          },
          ...prev,
        ]);
      }
    } catch (err) {
      console.error("Dashboard error:", err);
    }
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">System Overview</h1>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-900 p-4 rounded">
          <p>Total Users</p>
          <h2 className="text-2xl font-bold">5</h2>
        </div>

        <div className="bg-gray-900 p-4 rounded">
          <p>Active Sessions</p>
          <h2 className="text-2xl font-bold">2</h2>
        </div>

        <div className="bg-gray-900 p-4 rounded">
          <p>Risk Alerts</p>
          <h2 className="text-2xl font-bold">{alerts.length}</h2>
        </div>

        <div className="bg-gray-900 p-4 rounded">
          <p>Avg Risk Score</p>
          <h2 className="text-2xl font-bold">
            {(risk * 100).toFixed(2)}%
          </h2>
        </div>
      </div>

      <button
        onClick={handleEvent}
        className="bg-blue-600 px-4 py-2 rounded mb-6"
      >
        Send Event
      </button>

      <div className="bg-gray-900 p-4 rounded">
        <h2 className="text-lg font-semibold mb-2">Live Activity Feed</h2>

        {alerts.length === 0 && <p>No alerts yet</p>}

        {alerts.map((alert, index) => (
          <div key={index} className="border-b border-gray-700 py-2">
            <p className="text-red-400 font-semibold">ANOMALY</p>
            <p>{alert.message}</p>
            <p className="text-sm text-gray-400">{alert.time}</p>
          </div>
        ))}
      </div>
    </div>
  );
}