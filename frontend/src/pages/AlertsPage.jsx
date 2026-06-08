import { useMemo, useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Bot,
  ShieldAlert,
  TrendingUp,
  X,
  CheckCircle,
} from "lucide-react";
import {
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { getAlerts, getAnomalies, updateAlertStatus, getDashboardSummary } from "../services/api";

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtRisk(v) {
  return `${Math.round(Number(v || 0) * 100)}%`;
}

function riskColor(level) {
  if (level === "HIGH")     return "text-rose-400";
  if (level === "ELEVATED") return "text-amber-400";
  if (level === "GUARDED")  return "text-yellow-400";
  return "text-emerald-400";
}

function riskBorder(level) {
  if (level === "HIGH")     return "border-rose-500/30 bg-rose-500/10";
  if (level === "ELEVATED") return "border-amber-500/30 bg-amber-500/10";
  if (level === "GUARDED")  return "border-yellow-500/20 bg-yellow-500/5";
  return "border-emerald-500/20 bg-emerald-500/5";
}

const PIE_COLORS = {
  OPEN:     "#f43f5e",
  RESOLVED: "#10b981",
};

// ── Stat Row ───────────────────────────────────────────────────────────────

function StatRow({ label, value, accent = false }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 border-b border-white/5 last:border-0">
      <span className="text-sm text-slate-400">{label}</span>
      <span className={`text-sm font-semibold ${accent ? "text-cyan-300" : "text-slate-100"}`}>
        {value}
      </span>
    </div>
  );
}

// ── Anomaly Card (Collapsible) ─────────────────────────────────────────────

function AnomalyCard({ anom }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const features = [
    { label: "Z-Score Logon",       key: "z_logon" },
    { label: "Z-Score Devices",     key: "z_pcs" },
    { label: "Logon Deviation",     key: "logon_deviation" },
    { label: "Device Deviation",    key: "device_deviation" },
    { label: "Device Ratio",        key: "device_ratio" },
    { label: "Burst Score",         key: "burst_score" },
    { label: "Hour Deviation",      key: "hour_deviation" },
    { label: "Session Gap",         key: "session_gap" },
    { label: "Logon/Logoff Ratio",  key: "logon_logoff_ratio" },
  ];

  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] overflow-hidden transition-all duration-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3.5 text-left hover:bg-white/[0.04]"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-300 font-mono">{anom.batch_date}</span>
          <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${riskBorder(anom.risk_level)} ${riskColor(anom.risk_level)}`}>
            {anom.risk_level}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-white">{fmtRisk(anom.risk_score)}</span>
          <span className="text-slate-500 text-[10px]">{isExpanded ? "▲" : "▼"}</span>
        </div>
      </button>

      {isExpanded && (
        <div className="p-3.5 border-t border-white/5 space-y-4 bg-slate-950/40">
          {/* ML output */}
          <div className="space-y-1">
            <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">ML Output (V6)</h4>
            <StatRow label="Risk Score" value={fmtRisk(anom.risk_score)} accent />
            <StatRow label="Risk Level" value={anom.risk_level} />
            <StatRow label="HDBSCAN Cluster ID" value={anom.hdbscan_label !== undefined ? anom.hdbscan_label : "0"} />
            <StatRow label="HDBSCAN Cluster Prob" value={typeof anom.cluster_probability === "number" ? (anom.cluster_probability * 100).toFixed(1) + "%" : "100.0%"} />
            <StatRow label="Isolation Forest Score" value={typeof anom.anomaly_score === "number" ? anom.anomaly_score.toFixed(4) : "—"} />
            <StatRow label="Isolation Forest Anom" value={anom.if_anomaly ? "True" : "False"} />
            <StatRow label="Final Anomaly Flag" value={anom.anomaly_flag ? "True" : "False"} />
          </div>

          {/* Feature vector */}
          <div className="space-y-1">
            <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Feature Vector</h4>
            {features.map(({ label, key }) => {
              const val = anom[key] ?? (anom.feature_vector ? anom.feature_vector[key] : undefined);
              return (
                <StatRow
                  key={key}
                  label={label}
                  value={typeof val === "number" ? val.toFixed(4) : "—"}
                />
              );
            })}
            <StatRow label="Night Activity" value={(anom.night_activity_flag || (anom.feature_vector && anom.feature_vector.night_activity_flag)) ? "True" : "False"} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Alert Detail Drawer ───────────────────────────────────────────────────

function AlertDetailDrawer({ alert, onClose, onStatusChange }) {
  const [anomalies, setAnomalies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    async function loadAnomalies() {
      setIsLoading(true);
      try {
        const data = await getAnomalies(alert.user_id);
        // Filter anomalies that occurred up to the alert's batch date
        const filtered = (data || []).filter(
          (anom) => anom.batch_date <= alert.batch_date
        );
        setAnomalies(filtered);
      } catch (err) {
        console.error("Error loading user anomalies:", err);
      } finally {
        setIsLoading(false);
      }
    }
    if (alert?.user_id) {
      loadAnomalies();
    }
  }, [alert]);

  const handleToggleStatus = async () => {
    setIsUpdating(true);
    const newStatus = alert.status === "OPEN" ? "RESOLVED" : "OPEN";
    try {
      await updateAlertStatus(alert.alert_id, newStatus);
      onStatusChange(alert.alert_id, newStatus);
    } catch (err) {
      console.error("Failed to update status:", err);
      alert("Failed to update status: " + err.message);
    } finally {
      setIsUpdating(false);
    }
  };

  if (!alert) return null;

  return (
    <motion.div
      key="drawer"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 60 }}
      transition={{ duration: 0.22 }}
      className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-y-auto border-l border-white/10 bg-slate-950/95 shadow-2xl backdrop-blur-xl"
    >
      {/* Header */}
      <div className={`border-b border-white/10 p-6 ${alert.status === "OPEN" ? "border-rose-500/30 bg-rose-500/10" : "border-emerald-500/30 bg-emerald-500/10"}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              Alert Case Detail
            </p>
            <h2 className="mt-2 text-xl font-semibold text-white">{alert.full_name}</h2>
            <p className="mt-0.5 text-sm text-slate-400">
              {alert.employee_id} · {alert.department}
            </p>
          </div>
          <button
            onClick={onClose}
            className="mt-0.5 rounded-xl border border-white/10 bg-white/[0.05] p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"
          >
            <X size={16} />
          </button>
        </div>

        {/* Status and Action */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-widest ${
              alert.status === "OPEN"
                ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
            }`}>
              {alert.status}
            </span>
            <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs font-semibold uppercase tracking-widest text-slate-300">
              {alert.severity} Severity
            </span>
          </div>

          <button
            onClick={handleToggleStatus}
            disabled={isUpdating}
            className={`rounded-xl border px-4 py-2 text-xs font-bold uppercase tracking-wider transition ${
              alert.status === "OPEN"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                : "border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
            }`}
          >
            {isUpdating ? "Updating..." : alert.status === "OPEN" ? "Mark Resolved" : "Reopen Alert"}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 space-y-6 p-6">
        {/* Case Info */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Case Information</h3>
          <StatRow label="Full Name" value={alert.full_name} />
          <StatRow label="Employee ID" value={alert.employee_id} />
          <StatRow label="Department" value={alert.department} />
          <StatRow label="Role" value={alert.role || "—"} />
          <StatRow label="Trigger Date" value={alert.batch_date} />
          <StatRow label="Anomalous Weeks" value={`${alert.anomaly_count} weeks`} accent />
          <StatRow label="Lookback Window" value={`${alert.window_days} days`} />
        </div>

        {/* Underlying Anomalies */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Underlying Anomalies</h3>
          {isLoading ? (
            <div className="py-6 text-center text-xs text-slate-500">Loading anomalies...</div>
          ) : anomalies.length === 0 ? (
            <div className="py-6 text-center text-xs text-slate-500">No recent anomalies found.</div>
          ) : (
            <div className="space-y-2.5">
              {anomalies.map((anom) => (
                <AnomalyCard key={anom.score_id} anom={anom} />
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export function AlertsPage() {
  const [events, setEvents] = useState([]);
  const [weeklyTrends, setWeeklyTrends] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [filterLevel, setFilterLevel] = useState("ALL");

  const loadAlerts = async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await getAlerts();
      setEvents(data || []);
      
      const summary = await getDashboardSummary();
      if (summary?.weekly_trends) {
        setWeeklyTrends(summary.weekly_trends);
      }
    } catch (err) {
      setError(err.message || "Failed to load alerts.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleStatusChange = (alertId, newStatus) => {
    setEvents((prev) =>
      prev.map((evt) =>
        evt.alert_id === alertId ? { ...evt, status: newStatus } : evt
      )
    );
    setSelectedEvent((prev) =>
      prev && prev.alert_id === alertId ? { ...prev, status: newStatus } : prev
    );
  };

  // ── Derived analytics ────────────────────────────────────────────────────

  const openAlerts = useMemo(
    () => events.filter((e) => e.status === "OPEN"),
    [events],
  );

  const resolvedAlerts = useMemo(
    () => events.filter((e) => e.status === "RESOLVED"),
    [events],
  );

  // Status distribution for pie chart
  const alertStatusDist = useMemo(() => {
    const counts = { OPEN: openAlerts.length, RESOLVED: resolvedAlerts.length };
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value }));
  }, [openAlerts, resolvedAlerts]);

  // Timeline for area chart (weekly rate trends)
  const timeline = useMemo(
    () =>
      weeklyTrends.map((t) => ({
        label: t.batch_date,
        rate: t.anomaly_rate,
      })),
    [weeklyTrends],
  );

  // Filtered list for the alerts table
  const filteredAlerts = useMemo(
    () =>
      filterLevel === "ALL"
        ? events
        : events.filter((e) => e.status === filterLevel),
    [events, filterLevel],
  );

  const filterLevels = ["ALL", "OPEN", "RESOLVED"];

  const LEVEL_COLORS = {
    OPEN:     { text: "text-rose-300",   border: "border-rose-500/30 bg-rose-500/10" },
    RESOLVED: { text: "text-emerald-300",  border: "border-emerald-500/30 bg-emerald-500/10" },
    ALL:      { text: "text-cyan-300",   border: "border-cyan-400/20 bg-cyan-400/10" },
  };

  return (
    <div className="space-y-6 pb-4">
      {/* Drawer overlay */}
      <AnimatePresence>
        {selectedEvent && (
          <>
            <motion.div
              key="overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
              onClick={() => setSelectedEvent(null)}
            />
            <AlertDetailDrawer
              alert={selectedEvent}
              onClose={() => setSelectedEvent(null)}
              onStatusChange={handleStatusChange}
            />
          </>
        )}
      </AnimatePresence>

      {/* ── Header ── */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">Weekly Security Case File</p>
        <h1 className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white sm:text-4xl">
          <span className="inline-flex rounded-2xl border border-rose-400/20 bg-rose-400/10 p-3 text-rose-300">
            <ShieldAlert size={24} />
          </span>
          Security Cases
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-400">
          Review security alerts raised in the latest weekly batch run. Alerts indicate sustained anomalous behavior (&ge; 3 outliers in the lookback window). Resolve cases to mark them safe.
        </p>
      </section>

      {error && (
        <div className="rounded-[2rem] border border-rose-400/20 bg-rose-400/10 p-6 text-rose-200">
          {error}
        </div>
      )}

      {/* ── KPI strip ── */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Detected Alerts (This Week)",
            value: isLoading ? "..." : events.length,
            sub: "total weekly alerts raised",
            color: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
            icon: <Bot size={18} />,
          },
          {
            label: "Open Alerts (This Week)",
            value: isLoading ? "..." : openAlerts.length,
            sub: "critical unresolved threats",
            color: "border-rose-400/20 bg-rose-400/10 text-rose-300",
            icon: <ShieldAlert size={18} />,
          },
          {
            label: "Resolved Alerts (This Week)",
            value: isLoading ? "..." : resolvedAlerts.length,
            sub: "reviewed and marked safe",
            color: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
            icon: <CheckCircle size={18} />,
          },
          {
            label: "Flagged Users (This Week)",
            value: isLoading ? "..." : new Set(events.map((e) => e.user_id)).size,
            sub: "unique employees flagged",
            color: "border-indigo-400/20 bg-indigo-400/10 text-indigo-300",
            icon: <TrendingUp size={18} />,
          },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-400">{kpi.label}</p>
                <p className="mt-2 text-3xl font-bold text-white">{kpi.value}</p>
                <p className="mt-1 text-xs text-slate-500">{kpi.sub}</p>
              </div>
              <span className={`inline-flex rounded-xl border p-2.5 ${kpi.color}`}>
                {kpi.icon}
              </span>
            </div>
          </div>
        ))}
      </section>

      {/* ── Charts ── */}
      <section className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        {/* Weekly anomaly rate trends */}
        <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20">
          <h2 className="mb-1 text-base font-semibold text-white">Weekly Anomaly Trends</h2>
          <p className="mb-5 text-sm text-slate-400">Organization-wide average anomaly rate (%) across batch runs</p>
          {timeline.length > 0 ? (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="rateFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.1)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 'auto']} tickFormatter={(v) => `${Math.round(v)}%`} tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} width={40} />
                  <Tooltip
                    formatter={(v) => [`${Number(v).toFixed(1)}%`, "Anomaly Rate"]}
                    contentStyle={{ backgroundColor: "#020617", border: "1px solid rgba(148,163,184,0.16)", borderRadius: 12, color: "#f8fafc", fontSize: 12 }}
                  />
                  <Area type="monotone" dataKey="rate" stroke="#06b6d4" strokeWidth={2.5} fill="url(#rateFill)" dot={{ fill: "#06b6d4", r: 3 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-56 items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-500">
              {isLoading ? "Loading anomaly trends..." : "No trend data available."}
            </div>
          )}
        </div>

        {/* Alert status distribution pie */}
        <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20">
          <h2 className="mb-1 text-base font-semibold text-white">Alert Case Status</h2>
          <p className="mb-4 text-sm text-slate-400">Proportion of OPEN vs RESOLVED alerts</p>
          {alertStatusDist.length > 0 ? (
            <div className="flex items-center gap-4">
              <div className="h-32 w-32 shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={alertStatusDist} dataKey="value" cx="50%" cy="50%" innerRadius={28} outerRadius={52} paddingAngle={3}>
                      {alertStatusDist.map((entry) => (
                        <Cell key={entry.name} fill={PIE_COLORS[entry.name] ?? "#64748b"} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v, name) => [v, name]} contentStyle={{ backgroundColor: "#020617", border: "1px solid rgba(148,163,184,0.16)", borderRadius: 10, color: "#f8fafc", fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2">
                {alertStatusDist.map((entry) => (
                  <div key={entry.name} className="flex items-center gap-2 text-sm">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PIE_COLORS[entry.name] }} />
                    <span className="text-slate-400">{entry.name}</span>
                    <span className="ml-auto font-semibold text-white">{entry.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex h-32 items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-500">
              No alerts found.
            </div>
          )}
        </div>
      </section>

      {/* ── Alerts Table ── */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20">
        <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Active Alerts (This Week)</h2>
            <p className="mt-1 text-sm text-slate-400">
              Click any alert to review the underlying weekly anomalous metrics and features
            </p>
          </div>
          {/* Filter chips */}
          <div className="flex flex-wrap gap-2">
            {filterLevels.map((lvl) => {
              const styles = LEVEL_COLORS[lvl] ?? LEVEL_COLORS.ALL;
              return (
                <button
                  key={lvl}
                  onClick={() => setFilterLevel(lvl)}
                  className={`rounded-full border px-4 py-1.5 text-xs font-semibold uppercase tracking-widest transition ${
                    filterLevel === lvl
                      ? `${styles.border} ${styles.text}`
                      : "border-white/10 bg-white/[0.03] text-slate-500 hover:border-white/20 hover:text-slate-300"
                  }`}
                >
                  {lvl}
                </button>
              );
            })}
          </div>
        </div>

        {isLoading ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] py-12 text-center text-sm text-slate-500">
            Loading alerts...
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] py-12 text-center text-sm text-slate-500">
            No alerts match the selected status filter.
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence initial={false}>
              {filteredAlerts.map((evt) => (
                <motion.button
                  key={evt.alert_id}
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.18 }}
                  onClick={() => setSelectedEvent(evt)}
                  className={`w-full rounded-2xl border p-4 text-left transition-all hover:scale-[1.005] hover:shadow-lg ${
                    evt.status === "OPEN"
                      ? "border-rose-500/30 bg-rose-500/5 hover:bg-rose-500/10"
                      : "border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-3">
                    {/* Icon */}
                    <span className={`shrink-0 ${evt.status === "OPEN" ? "text-rose-400" : "text-emerald-400"}`}>
                      <ShieldAlert size={18} />
                    </span>

                    {/* User */}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-white">{evt.full_name}</p>
                      <p className="truncate text-xs text-slate-500">
                        {evt.employee_id} · {evt.department}
                      </p>
                    </div>

                    {/* Anomalous weeks count */}
                    <span className="text-xs text-slate-300 font-medium font-mono border border-white/10 bg-white/[0.03] px-2.5 py-1 rounded-lg">
                      {evt.anomaly_count} Anomalous Weeks
                    </span>

                    {/* Status badge */}
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-widest sm:inline-block ${
                      evt.status === "OPEN"
                        ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                        : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    }`}>
                      {evt.status}
                    </span>

                    {/* Role */}
                    <span className="hidden text-xs text-slate-500 xl:block font-medium">
                      {evt.role}
                    </span>

                    {/* Time */}
                    <span className="font-mono text-xs text-slate-500">Batch: {evt.batch_date}</span>
                  </div>
                </motion.button>
              ))}
            </AnimatePresence>
          </div>
        )}
      </section>
    </div>
  );
}
