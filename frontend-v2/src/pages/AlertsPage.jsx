import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Bot,
  ShieldAlert,
  TrendingUp,
  X,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { useLiveStore } from "../store/useLiveStore";

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtRisk(v) {
  return `${Math.round(Number(v || 0) * 100)}%`;
}

function fmtTime(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
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
  HIGH:     "#f43f5e",
  ELEVATED: "#f59e0b",
  GUARDED:  "#eab308",
  LOW:      "#10b981",
};

const SCENARIO_LABELS = {
  normal:          "Normal Day",
  burst_alert:     "Burst Attack",
  night_intrusion: "Night Intrusion",
  device_spread:   "Device Spread",
};

const SCENARIO_COLORS = {
  normal:          "#22d3ee",
  burst_alert:     "#f43f5e",
  night_intrusion: "#818cf8",
  device_spread:   "#f59e0b",
};

// ── Detail Drawer ──────────────────────────────────────────────────────────

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

function EventDetailDrawer({ event, onClose }) {
  if (!event) return null;

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
    <motion.div
      key="drawer"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 60 }}
      transition={{ duration: 0.22 }}
      className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-y-auto border-l border-white/10 bg-slate-950/95 shadow-2xl backdrop-blur-xl"
    >
      {/* Header */}
      <div className={`border-b border-white/10 p-6 ${riskBorder(event.risk_level)}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              Event Detail
            </p>
            <h2 className="mt-2 text-xl font-semibold text-white">{event.full_name}</h2>
            <p className="mt-0.5 text-sm text-slate-400">
              {event.employee_id} · {event.department}
            </p>
          </div>
          <button
            onClick={onClose}
            className="mt-0.5 rounded-xl border border-white/10 bg-white/[0.05] p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"
          >
            <X size={16} />
          </button>
        </div>

        {/* Risk level badge */}
        <div className="mt-4 flex items-center gap-3">
          <span className={`text-2xl font-bold ${riskColor(event.risk_level)}`}>
            {fmtRisk(event.risk_score)}
          </span>
          <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-widest ${riskBorder(event.risk_level)} ${riskColor(event.risk_level)}`}>
            {event.risk_level}
          </span>
          {event.anomaly_flag && (
            <span className="ml-auto rounded-full border border-rose-400/30 bg-rose-400/10 px-3 py-1 text-xs font-bold uppercase tracking-widest text-rose-300">
              Anomaly
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 space-y-5 p-6">

        {/* Identity */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Identity</h3>
          <StatRow label="Full name"    value={event.full_name} />
          <StatRow label="Employee ID"  value={event.employee_id} />
          <StatRow label="Department"   value={event.department} />
          <StatRow label="Role"         value={event.role || "—"} />
          <StatRow label="IP Address"   value={event.ip_address} />
        </div>

        {/* Event context */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Event Context</h3>
          <StatRow label="Timestamp"    value={new Date(event.timestamp).toLocaleString()} />
          <StatRow label="Logons"       value={event.logons} />
          <StatRow label="Devices"      value={event.devices} />
          <StatRow label="Scenario"     value={SCENARIO_LABELS[event.scenario] ?? event.scenario ?? "—"} />
          <StatRow label="Source"       value={event.source} />
          <StatRow label="Alert raised" value={event.alert_created ? "Yes" : "No"} />
        </div>

        {/* ML output */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">ML Output</h3>
          <StatRow label="Risk Score"    value={fmtRisk(event.risk_score)} accent />
          <StatRow label="Risk Level"    value={event.risk_level} />
          <StatRow label="Anomaly Score" value={typeof event.anomaly_score === "number" ? event.anomaly_score.toFixed(4) : "—"} />
          <StatRow label="Anomaly Flag"  value={event.anomaly_flag ? "True" : "False"} />
        </div>

        {/* Feature vector */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Feature Vector</h3>
          {features.map(({ label, key }) => {
            const val = event[key] ?? (event.features ? event.features[key] : undefined);
            return (
              <StatRow
                key={key}
                label={label}
                value={typeof val === "number" ? val.toFixed(4) : "—"}
              />
            );
          })}
          <StatRow label="Night Activity" value={event.night_activity_flag ? "True" : "False"} />
        </div>
      </div>
    </motion.div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export function AlertsPage() {
  const events     = useLiveStore((s) => s.events);
  const eventsCount = useLiveStore((s) => s.eventsCount);

  const [selectedEvent, setSelectedEvent] = useState(null);
  const [filterLevel, setFilterLevel] = useState("ALL");

  // ── Derived analytics ────────────────────────────────────────────────────

  const anomalies = useMemo(
    () => events.filter((e) => e.anomaly_flag),
    [events],
  );

  const alertsRaised = useMemo(
    () => events.filter((e) => e.alert_created),
    [events],
  );

  // Risk level distribution for pie chart
  const riskDist = useMemo(() => {
    const counts = { HIGH: 0, ELEVATED: 0, GUARDED: 0, LOW: 0 };
    anomalies.forEach((e) => { if (counts[e.risk_level] !== undefined) counts[e.risk_level]++; });
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value }));
  }, [anomalies]);

  // Scenario breakdown bar chart
  const scenarioDist = useMemo(() => {
    const counts = {};
    anomalies.forEach((e) => {
      const key = e.scenario || "normal";
      counts[key] = (counts[key] || 0) + 1;
    });
    return Object.entries(counts).map(([scenario, count]) => ({
      scenario: SCENARIO_LABELS[scenario] ?? scenario,
      count,
      fill: SCENARIO_COLORS[scenario] ?? "#64748b",
    }));
  }, [anomalies]);

  // Timeline for area chart — last 40 events, showing risk score
  const timeline = useMemo(
    () =>
      [...events]
        .reverse()
        .slice(-40)
        .map((e, i) => ({
          idx:      i,
          label:    fmtTime(e.timestamp),
          risk:     e.risk_score,
          anomaly:  e.anomaly_flag ? e.risk_score : null,
          scenario: e.scenario,
        })),
    [events],
  );

  // Filtered list for the event table
  const filteredAnomalies = useMemo(
    () =>
      filterLevel === "ALL"
        ? anomalies
        : anomalies.filter((e) => e.risk_level === filterLevel),
    [anomalies, filterLevel],
  );

  const filterLevels = ["ALL", "HIGH", "ELEVATED", "GUARDED"];

  const LEVEL_COLORS = {
    HIGH:     { text: "text-rose-300",   border: "border-rose-500/30 bg-rose-500/10" },
    ELEVATED: { text: "text-amber-300",  border: "border-amber-500/30 bg-amber-500/10" },
    GUARDED:  { text: "text-yellow-300", border: "border-yellow-500/20 bg-yellow-500/5" },
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
            <EventDetailDrawer event={selectedEvent} onClose={() => setSelectedEvent(null)} />
          </>
        )}
      </AnimatePresence>

      {/* ── Header ── */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">Session Intelligence</p>
        <h1 className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white sm:text-4xl">
          <span className="inline-flex rounded-2xl border border-rose-400/20 bg-rose-400/10 p-3 text-rose-300">
            <ShieldAlert size={24} />
          </span>
          Threat Dashboard
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-400">
          All anomalies and alerts detected by the ML pipeline during this session, streamed in real time.
          Click any event row for full user details and ML statistics.
        </p>
      </section>

      {/* ── KPI strip ── */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Total Events",
            value: eventsCount,
            sub: "scored this session",
            color: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
            icon: <Bot size={18} />,
          },
          {
            label: "Anomalies",
            value: anomalies.length,
            sub: `${eventsCount ? Math.round((anomalies.length / eventsCount) * 100) : 0}% of events`,
            color: "border-rose-400/20 bg-rose-400/10 text-rose-300",
            icon: <ShieldAlert size={18} />,
          },
          {
            label: "Alerts Raised",
            value: alertsRaised.length,
            sub: "new HIGH-risk alerts",
            color: "border-amber-400/20 bg-amber-400/10 text-amber-300",
            icon: <AlertTriangle size={18} />,
          },
          {
            label: "Users Flagged",
            value: new Set(anomalies.map((e) => e.user_id)).size,
            sub: "unique users anomalous",
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
        {/* Risk timeline */}
        <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20">
          <h2 className="mb-1 text-base font-semibold text-white">Risk Timeline</h2>
          <p className="mb-5 text-sm text-slate-400">Last 40 events — risk score over time with anomaly spikes highlighted</p>
          {timeline.length > 0 ? (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="riskFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="anomalyFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.55} />
                      <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.1)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} width={40} />
                  <Tooltip
                    formatter={(v, name) => [`${Math.round(v * 100)}%`, name === "risk" ? "Risk" : "Anomaly"]}
                    contentStyle={{ backgroundColor: "#020617", border: "1px solid rgba(148,163,184,0.16)", borderRadius: 12, color: "#f8fafc", fontSize: 12 }}
                  />
                  <Area type="monotone" dataKey="risk"    stroke="#22d3ee" strokeWidth={2} fill="url(#riskFill)"    dot={false} />
                  <Area type="monotone" dataKey="anomaly" stroke="#f43f5e" strokeWidth={2} fill="url(#anomalyFill)" dot={{ fill: "#f43f5e", r: 4 }} connectNulls={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-56 items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-500">
              Waiting for events…
            </div>
          )}
        </div>

        {/* Side charts column */}
        <div className="flex flex-col gap-6">
          {/* Risk distribution pie */}
          <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20">
            <h2 className="mb-1 text-base font-semibold text-white">Risk Distribution</h2>
            <p className="mb-4 text-sm text-slate-400">Anomalies by risk level</p>
            {riskDist.length > 0 ? (
              <div className="flex items-center gap-4">
                <div className="h-32 w-32 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={riskDist} dataKey="value" cx="50%" cy="50%" innerRadius={30} outerRadius={56} paddingAngle={3}>
                        {riskDist.map((entry) => (
                          <Cell key={entry.name} fill={PIE_COLORS[entry.name] ?? "#64748b"} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v, name) => [v, name]} contentStyle={{ backgroundColor: "#020617", border: "1px solid rgba(148,163,184,0.16)", borderRadius: 10, color: "#f8fafc", fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-2">
                  {riskDist.map((entry) => (
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
                No anomalies yet
              </div>
            )}
          </div>

          {/* Scenario breakdown */}
          <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20">
            <h2 className="mb-1 text-base font-semibold text-white">Scenario Breakdown</h2>
            <p className="mb-4 text-sm text-slate-400">Anomalies by threat type</p>
            {scenarioDist.length > 0 ? (
              <div className="h-28">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={scenarioDist} layout="vertical" margin={{ left: 0, right: 8 }}>
                    <XAxis type="number" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis type="category" dataKey="scenario" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} width={92} />
                    <Tooltip contentStyle={{ backgroundColor: "#020617", border: "1px solid rgba(148,163,184,0.16)", borderRadius: 10, color: "#f8fafc", fontSize: 12 }} />
                    <Bar dataKey="count" radius={[0, 5, 5, 0]}>
                      {scenarioDist.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-28 items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-500">
                No anomalies yet
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Anomaly Event Table ── */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20">
        <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Anomaly Events</h2>
            <p className="mt-1 text-sm text-slate-400">
              Click any row to inspect full user details and ML feature statistics
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

        {filteredAnomalies.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] py-12 text-center text-sm text-slate-500">
            {anomalies.length === 0
              ? "No anomalies detected yet — the ML engine is running…"
              : "No events match the selected filter."}
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence initial={false}>
              {filteredAnomalies.map((evt, i) => (
                <motion.button
                  key={`${evt.user_id}_${evt.timestamp}_${i}`}
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.18 }}
                  onClick={() => setSelectedEvent(evt)}
                  className={`w-full rounded-2xl border p-4 text-left transition-all hover:scale-[1.005] hover:shadow-lg ${
                    evt.risk_level === "HIGH"
                      ? "border-rose-500/30 bg-rose-500/5 hover:bg-rose-500/10"
                      : evt.risk_level === "ELEVATED"
                      ? "border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10"
                      : "border-white/10 bg-white/[0.02] hover:bg-white/[0.05]"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-3">
                    {/* Icon */}
                    <span className={`shrink-0 ${riskColor(evt.risk_level)}`}>
                      <ShieldAlert size={18} />
                    </span>

                    {/* User */}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-white">{evt.full_name}</p>
                      <p className="truncate text-xs text-slate-500">
                        {evt.employee_id} · {evt.department}
                      </p>
                    </div>

                    {/* Risk */}
                    <span className={`text-lg font-bold ${riskColor(evt.risk_level)}`}>
                      {fmtRisk(evt.risk_score)}
                    </span>

                    {/* Level badge */}
                    <span className={`hidden rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-widest sm:inline-block ${
                      evt.risk_level === "HIGH"     ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                      : evt.risk_level === "ELEVATED" ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                      : "border-yellow-500/20 bg-yellow-500/5 text-yellow-300"
                    }`}>
                      {evt.risk_level}
                    </span>

                    {/* Scenario */}
                    <span className="hidden text-xs text-slate-500 xl:block">
                      {SCENARIO_LABELS[evt.scenario] ?? evt.scenario ?? "—"}
                    </span>

                    {/* Time */}
                    <span className="font-mono text-xs text-slate-500">{fmtTime(evt.timestamp)}</span>

                    {/* Alert badge */}
                    {evt.alert_created && (
                      <span className="rounded-full border border-rose-400/30 bg-rose-400/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-rose-300">
                        Alert
                      </span>
                    )}
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
