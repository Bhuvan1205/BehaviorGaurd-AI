import { useRealTime } from "../context/RealTimeContext";

export default function Alerts() {
  const { alerts } = useRealTime();

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">Alerts</h1>

      {alerts.length === 0 && <p>No alerts yet</p>}

      {alerts.map((a, i) => (
        <div key={i} className="border-b py-2">
          <p>User: {a.user_id}</p>
          <p>Risk: {a.risk}</p>
          <p>Level: {a.level}</p>
        </div>
      ))}
    </div>
  );
}