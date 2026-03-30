import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Radar, RefreshCw, Shield, ShieldAlert, Wifi, WifiOff } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { openLiveStream, getHistory } from "../services/api";
import { useAppStore } from "../store/useAppStore";

function formatTimestamp(value, short = false) {
  if (!value) return "N/A";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: short ? undefined : "2-digit",
  }).format(new Date(value));
}

function formatRelativeTime(value) {
  if (!value) return "Unknown";
  const minutes = Math.round((new Date(value).getTime() - Date.now()) / 60000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
}

function formatRisk(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

const MAX_CHART_POINTS = 60;

export function MonitoringPage() {
  const selectedUserId = useAppStore((state) => state.selectedUserId);
  const users = useAppStore((state) => state.users);
  const selectedUser = useMemo(
    () => users.find((user) => user.user_id === selectedUserId) ?? null,
    [selectedUserId, users]
  );

  // Historical baseline loaded once
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  // Live stream state
  const [liveEvents, setLiveEvents] = useState([]);
  const [streamConnected, setStreamConnected] = useState(false);
  const streamRef = useRef(null);
  const tickerRef = useRef(null);

  // ── Load historical data for the selected user ──────────────────────────
  useEffect(() => {
    if (!selectedUserId) {
      setHistory([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError("");
    setLiveEvents([]);

    getHistory(selectedUserId)
      .then((data) => {
        setHistory(Array.isArray(data) ? data : []);
        setLastUpdated(new Date().toISOString());
      })
      .catch((e) => setError(e.message || "Unable to load history."))
      .finally(() => setIsLoading(false));
  }, [selectedUserId]);

  // ── SSE subscription — filter events for selected user ─────────────────
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.close();
      setStreamConnected(false);
    }
    if (!selectedUserId) return;

    const stream = openLiveStream(
      (evt) => {
        if (evt.type === "connected") {
          setStreamConnected(true);
          return;
        }

        // Only show events for the currently selected user
        if (evt.user_id !== selectedUserId) return;

        setStreamConnected(true);
        setLastUpdated(new Date().toISOString());

        const normalized = {
          event_timestamp: evt.timestamp || evt.event_timestamp,
          risk_score: evt.risk_score ?? evt.aggregated_risk ?? 0,
          anomaly_flag: Boolean(evt.anomaly_flag),
          risk_level: evt.risk_level || "LOW",
          logon_count: evt.logons || 0,
          device_count: evt.devices || 0,
          _live: true,
        };

        setLiveEvents((prev) => [normalized, ...prev]);
        // Also prepend to history (so chart updates immediately)
        setHistory((prev) => [normalized, ...prev].slice(0, 200));
      },
      () => setStreamConnected(false),
    );

    streamRef.current = stream;

    return () => {
      stream.close();
      setStreamConnected(false);
    };
  }, [selectedUserId]);

  // Auto-scroll ticker
  useEffect(() => {
    if (tickerRef.current) tickerRef.current.scrollTop = 0;
  }, [liveEvents]);

  // ── Chart data ──────────────────────────────────────────────────────────
  const chartData = useMemo(
    () =>
      [...history]
        .reverse()
        .slice(-MAX_CHART_POINTS)
        .map((item) => ({
          label: formatTimestamp(item.event_timestamp, true),
          risk: Number(item.risk_score || 0),
          timestamp: item.event_timestamp,
        })),
    [history]
  );

  const latestRisk = history[0]?.risk_score ?? 0;
  const anomalyCount = history.filter((item) => item.anomaly_flag).length;
  const liveAnomalies = liveEvents.filter((e) => e.anomaly_flag).length;

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">

      {/* Header */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">
              Live Feed
            </p>
            <h1 className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white sm:text-4xl">
              <span className="inline-flex rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-cyan-300">
                <Radar size={24} />
              </span>
              Monitoring
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
              Streaming live events for{" "}
              <span className="font-semibold text-slate-200">
                {selectedUser?.full_name ?? "the selected user"}
              </span>{" "}
              via SSE — updates the instant a new event is scored.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <div
              className={`inline-flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm font-medium ${
                streamConnected
                  ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
                  : "border-slate-500/20 bg-slate-500/10 text-slate-400"
              }`}
            >
              {streamConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
              {streamConnected ? "SSE live" : "Stream idle"}
            </div>
            <div className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
              <RefreshCw size={16} className={isLoading ? "animate-spin" : ""} />
              {lastUpdated
                ? `Updated ${formatRelativeTime(lastUpdated)}`
                : "Waiting for first event"}
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}
      </section>

      {/* KPI strip */}
      <section className="grid gap-4 xl:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-slate-400">History rows</p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {isLoading ? "…" : history.length}
          </p>
          <p className="mt-4 text-sm text-slate-500">Total scored windows on record.</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-slate-400">Latest risk</p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {isLoading ? "…" : formatRisk(latestRisk)}
          </p>
          <p className="mt-4 text-sm text-slate-500">Most recent risk score.</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-slate-400">Anomaly windows</p>
          <p className={`mt-3 text-3xl font-semibold ${anomalyCount > 0 ? "text-rose-400" : "text-white"}`}>
            {isLoading ? "…" : anomalyCount}
          </p>
          <p className="mt-4 text-sm text-slate-500">History rows flagged as anomalous.</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-slate-400">Live anomalies</p>
          <p className={`mt-3 text-3xl font-semibold ${liveAnomalies > 0 ? "text-amber-400" : "text-white"}`}>
            {liveAnomalies}
          </p>
          <p className="mt-4 text-sm text-slate-500">Anomalies in this session.</p>
        </div>
      </section>

      {/* Risk chart */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Risk timeline</h2>
            <p className="mt-1 text-sm text-slate-400">
              Updates in real time as events stream in via SSE.
            </p>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
            <Activity size={14} />
            Live
          </span>
        </div>

        {chartData.length > 0 ? (
          <div className="h-[22rem]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="monitoringRiskFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  domain={[0, 1]}
                  tickFormatter={(v) => `${Math.round(v * 100)}%`}
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={44}
                />
                <Tooltip
                  formatter={(v) => [formatRisk(v), "Risk score"]}
                  labelFormatter={(_, payload) =>
                    payload?.[0]?.payload?.timestamp
                      ? formatTimestamp(payload[0].payload.timestamp)
                      : "Timestamp"
                  }
                  contentStyle={{
                    backgroundColor: "#020617",
                    border: "1px solid rgba(148, 163, 184, 0.16)",
                    borderRadius: "16px",
                    color: "#f8fafc",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="risk"
                  stroke="#22d3ee"
                  strokeWidth={3}
                  fill="url(#monitoringRiskFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-[22rem] items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] text-sm text-slate-500">
            {isLoading ? "Loading…" : "No data yet. Select a user and start live_replay.py."}
          </div>
        )}
      </section>

      {/* Live event ticker for this user */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <h2 className="mb-4 text-base font-semibold text-white">
          Live events for {selectedUser?.full_name ?? "selected user"}
        </h2>

        <div ref={tickerRef} className="h-56 overflow-y-auto">
          {liveEvents.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              {selectedUserId
                ? streamConnected
                  ? "No events yet — start live_replay.py"
                  : "Stream idle — select a user"
                : "Select a user to monitor"}
            </div>
          ) : (
            <div className="space-y-1.5">
              <AnimatePresence initial={false}>
                {liveEvents.map((evt, i) => (
                  <motion.div
                    key={`${evt.event_timestamp}_${i}`}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 text-sm ${
                      evt.anomaly_flag
                        ? "border-rose-500/30 bg-rose-500/10"
                        : "border-white/8 bg-white/[0.02]"
                    }`}
                  >
                    {evt.anomaly_flag ? (
                      <ShieldAlert size={15} className="shrink-0 text-rose-400" />
                    ) : (
                      <Shield size={15} className="shrink-0 text-emerald-400/60" />
                    )}
                    <span className="font-mono text-xs text-slate-500">
                      {formatTimestamp(evt.event_timestamp)}
                    </span>
                    <span className="flex-1 text-slate-300">
                      {evt.logon_count} logon{evt.logon_count !== 1 ? "s" : ""},{" "}
                      {evt.device_count} device{evt.device_count !== 1 ? "s" : ""}
                    </span>
                    <span
                      className={`font-semibold ${
                        evt.risk_level === "HIGH"
                          ? "text-rose-400"
                          : evt.risk_level === "ELEVATED"
                          ? "text-amber-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {formatRisk(evt.risk_score)}
                    </span>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
