import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Radio,
  Shield,
  ShieldAlert,
  Users,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";
import { useLiveStore } from "../store/useLiveStore";

// ─── Helpers ────────────────────────────────────────────────────────────────

function riskColor(level) {
  if (level === "HIGH") return "text-rose-400";
  if (level === "ELEVATED") return "text-amber-400";
  if (level === "GUARDED") return "text-yellow-400";
  return "text-emerald-400";
}

function riskBorder(level) {
  if (level === "HIGH") return "border-rose-500/30 bg-rose-500/10";
  if (level === "ELEVATED") return "border-amber-500/30 bg-amber-500/10";
  if (level === "GUARDED") return "border-yellow-500/30 bg-yellow-500/10";
  return "border-emerald-500/20 bg-emerald-500/5";
}

function riskBar(score) {
  if (score >= 0.75) return "bg-rose-500";
  if (score >= 0.68) return "bg-amber-500";
  if (score >= 0.5) return "bg-yellow-400";
  return "bg-emerald-500";
}

function fmtTime(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function fmtRisk(v) {
  return `${Math.round(Number(v || 0) * 100)}%`;
}

const MAX_EVENTS = 80;
const BURST_THRESHOLD = 3;
const BURST_WINDOW_MS = 60_000;

const SCENARIO_META = {
  normal:           { label: "Normal Day",      icon: "🟢", color: "text-emerald-400", border: "border-emerald-400/30 bg-emerald-400/10" },
  burst_alert:      { label: "Burst Attack",     icon: "🔴", color: "text-rose-400",    border: "border-rose-500/30 bg-rose-500/10" },
  night_intrusion:  { label: "Night Intrusion",  icon: "🌙", color: "text-indigo-400",  border: "border-indigo-400/30 bg-indigo-400/10" },
  device_spread:    { label: "Device Spread",    icon: "💻", color: "text-amber-400",   border: "border-amber-400/30 bg-amber-400/10" },
};

// ─── Component ───────────────────────────────────────────────────────────────

export function LiveFeedPage() {
  // ── Read from global live store (persists across navigation) ────────────
  const events       = useLiveStore((s) => s.events);
  const connected    = useLiveStore((s) => s.connected);
  const connectionError = useLiveStore((s) => s.connectionError);
  const eventsCount  = useLiveStore((s) => s.eventsCount);
  const burstAlert   = useLiveStore((s) => s.burstAlert);
  const scoreboard   = useLiveStore((s) => s.scoreboard);

  const [filterRiskOnly, setFilterRiskOnly] = useState(false);

  const tickerRef = useRef(null);

  // Auto-scroll ticker
  useEffect(() => {
    if (tickerRef.current) tickerRef.current.scrollTop = 0;
  }, [events]);

  // ── Derived data ────────────────────────────────────────────────────────

  const displayEvents = filterRiskOnly
    ? events.filter((e) => e.anomaly_flag)
    : events;

  const sortedScoreboard = Object.values(scoreboard)
    .sort((a, b) => b.risk_score - a.risk_score)
    .slice(0, 10);

  const anomalyCount = events.filter((e) => e.anomaly_flag).length;


  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">
              Operations Center
            </p>
            <h1 className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white sm:text-4xl">
              <span className="inline-flex rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-cyan-300">
                <Radio size={24} />
              </span>
              Live Threat Feed
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400">
              Risk scores from the daily log batch runs — updated dynamically as the batch
              pipeline processes new logs.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            {/* Connection status */}
            <div
              className={`inline-flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm font-medium transition-colors ${
                connected
                  ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
                  : "border-slate-500/20 bg-slate-500/10 text-slate-400"
              }`}
            >
              {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
              {connected ? "Polling Active" : "Checking Feed..."}
            </div>

            {/* Burst badge */}
            <AnimatePresence>
              {burstAlert && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="inline-flex animate-pulse items-center gap-2 rounded-2xl border border-rose-400/40 bg-rose-500/20 px-4 py-3 text-sm font-bold text-rose-200"
                >
                  <Zap size={16} />
                  BURST DETECTED
                </motion.div>
              )}
            </AnimatePresence>

            {/* Stats */}
            <div className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
              <Activity size={16} />
              {eventsCount} events
            </div>
          </div>
        </div>

        {connectionError && (
          <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
            {connectionError}
          </div>
        )}
      </section>



      {/* ── KPI strip ── */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6">
          <p className="text-sm font-medium text-slate-400">Events this session</p>
          <p className="mt-3 text-3xl font-semibold text-white">{eventsCount}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6">
          <p className="text-sm font-medium text-slate-400">Anomalies detected</p>
          <p className={`mt-3 text-3xl font-semibold ${anomalyCount > 0 ? "text-rose-400" : "text-white"}`}>
            {anomalyCount}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6">
          <p className="text-sm font-medium text-slate-400">Users tracked</p>
          <p className="mt-3 text-3xl font-semibold text-white">{Object.keys(scoreboard).length}</p>
        </div>
      </div>

      {/* ── Main two-column layout ── */}
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">

        {/* ── Event Ticker ── */}
        <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/20">
          <div className="flex items-center justify-between border-b border-white/10 p-6">
            <div>
              <h2 className="text-base font-semibold text-white">Live Event Ticker</h2>
              <p className="mt-1 text-sm text-slate-400">
                {filterRiskOnly ? "Showing anomalies only" : `Showing all events (last ${MAX_EVENTS})`}
              </p>
            </div>
            <button
              onClick={() => setFilterRiskOnly((v) => !v)}
              className={`rounded-xl border px-3 py-1.5 text-xs font-medium transition-colors ${
                filterRiskOnly
                  ? "border-rose-400/40 bg-rose-400/10 text-rose-200"
                  : "border-white/10 bg-white/[0.04] text-slate-300 hover:border-white/20"
              }`}
            >
              {filterRiskOnly ? "Anomalies only" : "All events"}
            </button>
          </div>

          <div ref={tickerRef} className="h-[540px] overflow-y-auto p-3">
            {displayEvents.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">
                {connected
                  ? "Waiting for events… Upload a daily log CSV in the Upload section to run the pipeline."
                  : "Checking threat feed…"}
              </div>
            ) : (
              <div className="space-y-1.5">
                <AnimatePresence initial={false}>
                  {displayEvents.map((evt, idx) => (
                    <motion.div
                      key={`${evt.user_id}_${evt.timestamp}_${idx}`}
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                      className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 text-sm ${riskBorder(evt.risk_level)}`}
                    >
                      {/* Risk icon */}
                      <span className="shrink-0">
                        {evt.anomaly_flag ? (
                          <ShieldAlert size={16} className="text-rose-400" />
                        ) : (
                          <Shield size={16} className="text-emerald-400/60" />
                        )}
                      </span>

                      {/* Time */}
                      <span className="w-20 shrink-0 font-mono text-xs text-slate-500">
                        {fmtTime(evt.timestamp)}
                      </span>

                      {/* User */}
                      <span className="min-w-0 flex-1 truncate font-medium text-slate-200">
                        {evt.full_name}
                      </span>

                      {/* Department */}
                      <span className="hidden shrink-0 text-xs text-slate-500 sm:block">
                        {evt.department}
                      </span>

                      {/* Risk */}
                      <span className={`shrink-0 font-semibold ${riskColor(evt.risk_level)}`}>
                        {fmtRisk(evt.risk_score)}
                      </span>

                      {/* Source badge */}
                      {evt.source === "replay_anomaly" && (
                        <span className="shrink-0 rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-rose-300">
                          ANOMALY
                        </span>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </div>
        </section>

        {/* ── Risk Scoreboard ── */}
        <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/20">
          <div className="border-b border-white/10 p-6">
            <h2 className="text-base font-semibold text-white">Risk Scoreboard</h2>
            <p className="mt-1 text-sm text-slate-400">
              Peak risk per employee seen this session
            </p>
          </div>

          <div className="h-[540px] overflow-y-auto p-4">
            {sortedScoreboard.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">
                No data yet
              </div>
            ) : (
              <div className="space-y-2">
                {sortedScoreboard.map((user, i) => (
                  <div
                    key={user.user_id}
                    className={`rounded-xl border p-3 ${riskBorder(user.risk_level)}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="shrink-0 text-xs font-bold text-slate-500">
                          #{i + 1}
                        </span>
                        <span className="min-w-0 truncate text-sm font-medium text-slate-200">
                          {user.full_name}
                        </span>
                      </div>
                      <span className={`shrink-0 text-sm font-bold ${riskColor(user.risk_level)}`}>
                        {fmtRisk(user.risk_score)}
                      </span>
                    </div>
                    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${riskBar(user.risk_score)}`}
                        style={{ width: `${Math.round(user.risk_score * 100)}%` }}
                      />
                    </div>
                    <p className="mt-1.5 text-[11px] text-slate-500">
                      {user.department} · last {fmtTime(user.last_seen)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
