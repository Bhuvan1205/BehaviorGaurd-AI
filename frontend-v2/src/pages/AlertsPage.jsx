import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { getAlerts } from "../services/api";
import { useAppStore } from "../store/useAppStore";

function formatTimestamp(value) {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function severityClasses(severity) {
  if (severity === "HIGH") {
    return "border-rose-400/20 bg-rose-400/10 text-rose-200";
  }

  return "border-white/10 bg-white/[0.04] text-slate-200";
}

function statusClasses(status) {
  if (status === "OPEN") {
    return "border-amber-400/20 bg-amber-400/10 text-amber-200";
  }

  return "border-emerald-400/20 bg-emerald-400/10 text-emerald-200";
}

export function AlertsPage() {
  const selectedUserId = useAppStore((state) => state.selectedUserId);
  const users = useAppStore((state) => state.users);
  const selectedUser = useMemo(
    () => users.find((user) => user.user_id === selectedUserId) ?? null,
    [selectedUserId, users]
  );

  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const loadAlerts = async () => {
    if (!selectedUserId) {
      setAlerts([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const data = await getAlerts(selectedUserId);
      setAlerts(Array.isArray(data) ? data : []);
    } catch (requestError) {
      setError(requestError.message || "Unable to load alerts.");
      setAlerts([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [selectedUserId]);

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">Triage</p>
            <h1 className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white sm:text-4xl">
              <span className="inline-flex rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-cyan-300">
                <AlertTriangle size={24} />
              </span>
              Alerts
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
              Live alert records for <span className="font-semibold text-slate-200">{selectedUser?.full_name ?? "the selected user"}</span>.
            </p>
          </div>

          <button
            type="button"
            onClick={loadAlerts}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/[0.08]"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {error ? (
          <div className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        ) : null}
      </section>

      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Alert table</h2>
            <p className="mt-1 text-sm text-slate-400">Showing alert ID, severity, status, and creation time.</p>
          </div>
          <span className="text-sm text-slate-500">{isLoading ? "Loading..." : `${alerts.length} alerts`}</span>
        </div>

        {alerts.length > 0 ? (
          <div className="overflow-hidden rounded-2xl border border-white/10">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-white/10">
                <thead className="bg-white/[0.03]">
                  <tr>
                    <th className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">alert_id</th>
                    <th className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">severity</th>
                    <th className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">status</th>
                    <th className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">created_at</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 bg-slate-950/40">
                  {alerts.map((alert) => (
                    <tr key={alert.alert_id} className="transition hover:bg-white/[0.03]">
                      <td className="px-5 py-4 text-sm font-medium text-white">{alert.alert_id}</td>
                      <td className="px-5 py-4">
                        <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${severityClasses(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${statusClasses(alert.status)}`}>
                          {alert.status}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-300">{formatTimestamp(alert.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-6 text-sm text-slate-500">
            {isLoading ? "Loading alerts..." : "No alerts found for the selected user."}
          </div>
        )}
      </section>
    </div>
  );
}
