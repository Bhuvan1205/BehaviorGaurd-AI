import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarClock,
  Mail,
  ShieldUser,
  TriangleAlert,
  UserRound,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useParams } from "react-router-dom";
import { getAlerts, getHistory, getUserDetail } from "../services/api";
import { useAppStore } from "../store/useAppStore";

function formatRisk(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function formatEmployeeId(employeeId) {
  return employeeId?.replace(/^DEMO-/, "") || "N/A";
}

function formatTimestamp(value, short = false) {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: short ? undefined : "2-digit",
    minute: short ? undefined : "2-digit",
  }).format(new Date(value));
}

function formatRelativeTime(value) {
  if (!value) {
    return "Unknown";
  }

  const minutes = Math.round((new Date(value).getTime() - Date.now()) / 60000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  if (Math.abs(minutes) < 60) {
    return formatter.format(minutes, "minute");
  }

  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) {
    return formatter.format(hours, "hour");
  }

  return formatter.format(Math.round(hours / 24), "day");
}

function SectionCard({ title, subtitle, action, children }) {
  return (
    <section className="rounded-[1.9rem] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function UserDetailPage() {
  const { id } = useParams();
  const selectedUserId = useAppStore((state) => state.selectedUserId);
  const users = useAppStore((state) => state.users);
  const selectUser = useAppStore((state) => state.selectUser);
  const effectiveUserId = id || selectedUserId;
  const selectedDirectoryUser = useMemo(
    () => users.find((user) => user.user_id === effectiveUserId) ?? null,
    [effectiveUserId, users]
  );
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!effectiveUserId) {
      setUser(null);
      setHistory([]);
      setAlerts([]);
      setIsLoading(false);
      return;
    }

    selectUser(effectiveUserId);
    let isMounted = true;

    const loadUser = async () => {
      setIsLoading(true);
      setError("");

      try {
        const [userData, historyData, alertsData] = await Promise.all([
          getUserDetail(effectiveUserId),
          getHistory(effectiveUserId),
          getAlerts(effectiveUserId),
        ]);

        if (!isMounted) {
          return;
        }

        setUser(userData);
        setHistory(Array.isArray(historyData) ? historyData : []);
        setAlerts(Array.isArray(alertsData) ? alertsData : []);
      } catch (requestError) {
        if (isMounted) {
          setError(requestError.message || "Unable to load user detail.");
          setUser(null);
          setHistory([]);
          setAlerts([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadUser();

    return () => {
      isMounted = false;
    };
  }, [effectiveUserId, selectUser]);

  const riskTrendData = useMemo(
    () =>
      [...history].reverse().map((item) => ({
        label: formatTimestamp(item.event_timestamp, true),
        risk: Number(item.risk_score || 0),
        timestamp: item.event_timestamp,
      })),
    [history]
  );

  const activityPatternData = useMemo(() => {
    const buckets = {};

    history.forEach((item) => {
      const eventTime = item.event_timestamp ? new Date(item.event_timestamp) : null;
      const label = eventTime
        ? `${String(eventTime.getHours()).padStart(2, "0")}:00`
        : "Unknown";

      if (!buckets[label]) {
        buckets[label] = { hour: label, windows: 0, anomalies: 0 };
      }

      buckets[label].windows += 1;
      buckets[label].anomalies += item.anomaly_flag ? 1 : 0;
    });

    return Object.values(buckets).sort((a, b) => a.hour.localeCompare(b.hour)).slice(0, 8);
  }, [history]);

  const latestAlerts = alerts.slice(0, 4);

  if (!effectiveUserId) {
    return (
      <div className="space-y-6">
        <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-8 shadow-2xl shadow-black/20">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">
            User Analytics
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">
            Select an investigation target
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
            This workspace is dedicated to individual user analysis. Choose a target from the left
            sidebar to load user-specific identity, risk, and alert context.
          </p>
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-[2rem] border border-rose-400/20 bg-rose-400/10 p-8 text-rose-200">
        {error}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-8 text-slate-400">
        Loading user detail...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-8 text-slate-400">
        No user detail available.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">Identity Lens</p>
        <h1 className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white sm:text-4xl">
          <span className="inline-flex rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-cyan-300">
            <ShieldUser size={24} />
          </span>
          {user.full_name}
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
          Detailed user context pulled live from PostgreSQL for employee {formatEmployeeId(user.employee_id)}.
        </p>
        {selectedDirectoryUser ? (
          <p className="mt-3 text-sm text-slate-500">
            Investigation target currently selected in the workspace:
            <span className="ml-2 font-medium text-slate-300">{selectedDirectoryUser.full_name}</span>
          </p>
        ) : null}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-slate-400">Current role</p>
          <p className="mt-3 text-2xl font-semibold text-white">{user.role_name}</p>
          <p className="mt-4 text-sm text-slate-500">{user.department_name}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-slate-400">Latest risk</p>
          <p className="mt-3 text-2xl font-semibold text-white">{formatRisk(user.latest_risk)}</p>
          <p className="mt-4 text-sm text-slate-500">{user.latest_risk_level}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-slate-400">Open alerts</p>
          <p className="mt-3 text-2xl font-semibold text-white">{user.open_alert_count}</p>
          <p className="mt-4 text-sm text-slate-500">{user.alert_count} total alert records</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-slate-400">History windows</p>
          <p className="mt-3 text-2xl font-semibold text-white">{user.history_count}</p>
          <p className="mt-4 text-sm text-slate-500">{user.anomaly_count} anomaly windows</p>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <SectionCard
          title="Risk trend"
          subtitle="How this user's risk windows have moved over recent activity"
          action={
            <span className="inline-flex items-center gap-2 text-sm text-slate-500">
              <CalendarClock size={16} />
              {history.length} windows
            </span>
          }
        >
          {riskTrendData.length > 0 ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={riskTrendData}>
                  <defs>
                    <linearGradient id="userRiskTrend" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                      <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis
                    domain={[0, 1]}
                    tickFormatter={(value) => `${Math.round(value * 100)}%`}
                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    width={44}
                  />
                  <Tooltip
                    formatter={(value) => [formatRisk(value), "Risk score"]}
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
                  <Area type="monotone" dataKey="risk" stroke="#22d3ee" strokeWidth={3} fill="url(#userRiskTrend)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-80 items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] text-sm text-slate-500">
              No user risk history available yet.
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="Alert timeline"
          subtitle="Most recent analyst-visible alert activity for this user"
          action={<span className="text-sm font-medium text-slate-500">{alerts.length} alerts</span>}
        >
          <div className="space-y-3">
            {latestAlerts.length > 0 ? (
              latestAlerts.map((alert) => (
                <div key={alert.alert_id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">Alert #{alert.alert_id}</p>
                      <p className="mt-1 text-sm text-slate-400">
                        Created {formatRelativeTime(alert.created_at)}
                      </p>
                    </div>
                    <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-amber-300">
                      {alert.status}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-6 text-sm text-slate-500">
                No alerts recorded for this user.
              </div>
            )}
          </div>
        </SectionCard>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <SectionCard
          title="Activity pattern by hour"
          subtitle="Distribution of recent behavior windows and anomaly concentration"
        >
          {activityPatternData.length > 0 ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={activityPatternData}>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
                  <XAxis dataKey="hour" tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} width={44} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#020617",
                      border: "1px solid rgba(148, 163, 184, 0.16)",
                      borderRadius: "16px",
                      color: "#f8fafc",
                    }}
                  />
                  <Bar dataKey="windows" fill="#38bdf8" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="anomalies" fill="#f59e0b" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-72 items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] text-sm text-slate-500">
              Not enough history to draw activity patterns yet.
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="Current investigation notes"
          subtitle="Quick interpretation of the selected user's present posture"
          action={
            <span className="inline-flex items-center gap-2 text-sm text-slate-500">
              <AlertTriangle size={16} />
              Live summary
            </span>
          }
        >
          <div className="space-y-3 text-sm text-slate-300">
            <p className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              Average risk remains at <span className="font-semibold text-white">{formatRisk(user.avg_risk)}</span>.
            </p>
            <p className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              Latest observed window is categorized as <span className="font-semibold text-white">{user.latest_risk_level}</span>.
            </p>
            <p className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              This user currently has <span className="font-semibold text-white">{user.open_alert_count}</span> open alerts visible to analysts.
            </p>
          </div>
        </SectionCard>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <div className="flex items-start gap-3">
            <span className="rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-cyan-300">
              <UserRound size={20} />
            </span>
            <div>
              <h2 className="text-lg font-semibold text-white">Identity</h2>
              <p className="mt-1 text-sm text-slate-400">Directory metadata for the selected employee.</p>
            </div>
          </div>
          <div className="mt-6 space-y-3 text-sm text-slate-300">
            <p><span className="text-slate-500">Employee ID:</span> {formatEmployeeId(user.employee_id)}</p>
            <p><span className="text-slate-500">Department:</span> {user.department_name}</p>
            <p><span className="text-slate-500">Role:</span> {user.role_name}</p>
            <p><span className="text-slate-500">Status:</span> {user.status}</p>
            <p><span className="text-slate-500">Hire date:</span> {user.hire_date ?? "N/A"}</p>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <div className="flex items-start gap-3">
            <span className="rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-cyan-300">
              <Mail size={20} />
            </span>
            <div>
              <h2 className="text-lg font-semibold text-white">Contact and risk posture</h2>
              <p className="mt-1 text-sm text-slate-400">Useful talking points for the live demo walkthrough.</p>
            </div>
          </div>
          <div className="mt-6 space-y-3 text-sm text-slate-300">
            <p><span className="text-slate-500">Email:</span> {user.email}</p>
            <p><span className="text-slate-500">Average risk:</span> {formatRisk(user.avg_risk)}</p>
            <p><span className="text-slate-500">Latest event:</span> {user.latest_event_timestamp ?? "N/A"}</p>
            <p className="flex items-center gap-2">
              <TriangleAlert size={16} className="text-amber-300" />
              <span>{user.open_alert_count > 0 ? "User currently has open analyst-visible alerts." : "User currently has no open alerts."}</span>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
