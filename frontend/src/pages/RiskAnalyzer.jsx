import { useState } from "react";
import { useRealTime } from "../context/RealTimeContext";

export default function RiskAnalyzer() {
  const { processEvent, lastResult, userHistory } = useRealTime();

  const [logons, setLogons] = useState(1);
  const [devices, setDevices] = useState(1);
  const [loading, setLoading] = useState(false);

  async function handleAnalyze() {
    try {
      setLoading(true);

      await processEvent({
        userId: "user_123",
        logons: Number(logons),
        devices: Number(devices),
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">Risk Analyzer</h1>

      <div className="flex gap-4 mb-4">
        <input
          type="number"
          value={logons}
          onChange={(e) => setLogons(e.target.value)}
          className="text-black px-2 py-1"
        />
        <input
          type="number"
          value={devices}
          onChange={(e) => setDevices(e.target.value)}
          className="text-black px-2 py-1"
        />
      </div>

      <button
        onClick={handleAnalyze}
        className="bg-blue-600 px-4 py-2 rounded"
      >
        {loading ? "Processing..." : "Send Event"}
      </button>

      {lastResult && (
        <div className="mt-6">
          <p>Risk: {lastResult.aggregated_risk}</p>
          <p>Level: {lastResult.alert.level}</p>
        </div>
      )}

      <p className="mt-4 text-gray-400">
        History Size: {userHistory.length}
      </p>
    </div>
  );
}