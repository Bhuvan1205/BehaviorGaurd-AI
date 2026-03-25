import { useEffect, useState } from "react";
import { useRealTime } from "../context/RealTimeContext";

export default function Monitoring() {
  const { processEvent, lastResult } = useRealTime();
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let interval;

    if (running) {
      interval = setInterval(() => {
        processEvent({
          userId: "user_123",
          logons: Math.floor(Math.random() * 10) + 1,
          devices: Math.floor(Math.random() * 3) + 1,
        });
      }, 3000);
    }

    return () => clearInterval(interval);
  }, [running]);

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">Monitoring</h1>

      <button
        onClick={() => setRunning(!running)}
        className="bg-blue-600 px-4 py-2 rounded"
      >
        {running ? "Stop Monitoring" : "Start Monitoring"}
      </button>

      {lastResult && (
        <div className="mt-6">
          <p>Risk: {lastResult.aggregated_risk}</p>
          <p>Level: {lastResult.alert.level}</p>
        </div>
      )}
    </div>
  );
}