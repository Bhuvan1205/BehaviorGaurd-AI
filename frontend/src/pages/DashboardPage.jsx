import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Building2,
  CalendarClock,
  ChevronRight,
  RefreshCw,
  ShieldAlert,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  AreaChart,
  Area,
} from "recharts";
import { Link } from "react-router-dom";
import { getDashboardSummary } from "../services/api";
import { useAppStore } from "../store/useAppStore";

function formatRisk(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function formatEmployeeId(employeeId) {
  return employeeId?.replace(/^DEMO-/, "") || "N/A";
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

function KpiCard({ title, value, hint, icon: Icon, tone }) {
  const toneStyles = {
    cyan: "bg-cyan-400/10 text-cyan-300 ring-cyan-400/20",
    amber: "bg-amber-400/10 text-amber-300 ring-amber-400/20",
    emerald: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
    sky: "bg-sky-400/10 text-sky-300 ring-sky-400/20",
  };

  return (
    <div className="rounded-[1.8rem] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-400">{title}</p>
          <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
        </div>
        <span className={`inline-flex rounded-[1.1rem] p-3 ring-1 ${toneStyles[tone]}`}>
          <Icon size={20} />
        </span>
      </div>
      <p className="mt-4 text-sm text-slate-500">{hint}</p>
    </div>
  );
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

export function DashboardPage() {
  const usersError = useAppStore((state) => state.usersError);
  const selectedUserId = useAppStore((state) => state.selectedUserId);
  const users = useAppStore((state) => state.users);
  const selectUser = useAppStore((state) => state.selectUser);
  const selectedUser = users.find((user) => user.user_id === selectedUserId) ?? null;

  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async () => {
    setIsLoading(true);
    setError("");

    try {
      const summaryData = await getDashboardSummary();
      setSummary(summaryData);
    } catch (requestError) {
      setError(requestError.message || "Unable to load dashboard data.");
      setSummary(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    const id = setInterval(loadDashboard, 30000); // refresh every 30s
    return () => clearInterval(id);
  }, []);

  const orgRiskData = summary?.risk_distribution ?? [];
  const topUsers = summary?.top_users ?? [];
  const recentAlerts = summary?.recent_alerts ?? [];
  const departmentRollup = summary?.department_rollup ?? [];
  const orgTotals = summary?.totals ?? {};

  return (
    <div className="space-y-6 pb-2">
      <section className="rounded-[2.2rem] border border-white/10 bg-slate-950/72 px-6 py-8 text-center shadow-2xl shadow-black/20 sm:px-10">
        <p className="text-[11px] font-semibold uppercase tracking-[0.34em] text-cyan-400">
          Organization Overview
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.03em] text-white sm:text-5xl">
          Enterprise security analytics
        </h1>
        <p className="mx-auto mt-4 max-w-3xl text-sm leading-7 text-slate-400 sm:text-base">
          This dashboard is now dedicated to the full organization. Individual investigation
          analytics are handled separately so the overall security posture stays clear and focused.
        </p>

        <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <button
            type="button"
            onClick={() => {
              selectUser("");
              loadDashboard();
            }}
            className="inline-flex items-center justify-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-5 py-2.5 text-sm font-medium text-slate-100 transition hover:bg-white/[0.08]"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
          <Link
            to={selectedUserId ? `/user/${selectedUserId}` : "/user-analytics"}
            className="inline-flex items-center justify-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-5 py-2.5 text-sm font-medium text-cyan-200 transition hover:bg-cyan-400/15"
          >
            User analytics
            <ChevronRight size={16} />
          </Link>
        </div>

        {selectedUser ? (
          <p className="mt-5 text-sm text-slate-500">
            Current investigation target:
            <span className="ml-2 font-medium text-slate-300">
              {selectedUser.full_name} ({formatEmployeeId(selectedUser.employee_id)})
            </span>
          </p>
        ) : (
          <p className="mt-5 text-sm text-slate-500">
            No investigation target is selected by default. Choose one from the sidebar when you
            want individual user analytics.
          </p>
        )}

        {usersError || error ? (
          <div className="mx-auto mt-6 max-w-3xl rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
            {usersError || error}
          </div>
        ) : null}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="Active users"
          value={isLoading ? "..." : orgTotals.active_users ?? 0}
          hint="Active employee records in the monitored organization."
          icon={Users}
          tone="sky"
        />
        <KpiCard
          title="Open alerts"
          value={isLoading ? "..." : orgTotals.alerts_open ?? 0}
          hint="Alerts that currently require analyst attention."
          icon={AlertTriangle}
          tone="amber"
        />
        <KpiCard
          title="Org avg risk"
          value={isLoading ? "..." : formatRisk(orgTotals.avg_risk)}
          hint="Average risk score across all stored behavior windows."
          icon={ShieldAlert}
          tone="emerald"
        />
        <KpiCard
          title="Departments"
          value={isLoading ? "..." : orgTotals.departments ?? 0}
          hint="Departments represented in the current dataset."
          icon={Building2}
          tone="cyan"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <SectionCard
          title="Organization risk distribution (Latest Weekly Batch)"
          subtitle="Current spread of low, guarded, elevated, and high-risk windows"
          action={
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
              Batch Distribution
            </span>
          }
        >
          {orgRiskData.length > 0 ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={orgRiskData}>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
                  <XAxis dataKey="band" tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} width={44} />
                  <Tooltip
                    formatter={(value) => [value, "Windows"]}
                    contentStyle={{
                      backgroundColor: "#020617",
                      border: "1px solid rgba(148, 163, 184, 0.16)",
                      borderRadius: "16px",
                      color: "#f8fafc",
                    }}
                  />
                  <Bar dataKey="count" fill="#22d3ee" radius={[10, 10, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-80 items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] text-sm text-slate-500">
              {isLoading ? "Loading organization summary..." : "No organization analytics found."}
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="Weekly Anomaly Trends"
          subtitle="Historical timeline of average anomaly rate (%) over previous weeks"
          action={
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
              Timeline
            </span>
          }
        >
          {summary?.weekly_trends?.length > 0 ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={summary.weekly_trends}>
                  <defs>
                    <linearGradient id="weeklyAnomalyTrend" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                      <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
                  <XAxis 
                    dataKey="batch_date" 
                    tick={{ fill: "#94a3b8", fontSize: 11 }} 
                    tickLine={false} 
                    axisLine={false} 
                  />
                  <YAxis 
                    tickFormatter={(value) => `${Math.round(value)}%`}
                    tick={{ fill: "#94a3b8", fontSize: 11 }} 
                    tickLine={false} 
                    axisLine={false} 
                    width={40} 
                  />
                  <Tooltip
                    formatter={(value) => [`${Number(value).toFixed(1)}%`, "Anomaly Rate"]}
                    labelFormatter={(label) => `Batch ending: ${label}`}
                    contentStyle={{
                      backgroundColor: "#020617",
                      border: "1px solid rgba(148, 163, 184, 0.16)",
                      borderRadius: "16px",
                      color: "#f8fafc",
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="anomaly_rate" 
                    stroke="#22d3ee" 
                    strokeWidth={3} 
                    fill="url(#weeklyAnomalyTrend)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-80 items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] text-sm text-slate-500">
              {isLoading ? "Loading trend analysis..." : "No weekly batch history found."}
            </div>
          )}
        </SectionCard>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard
          title="Top risky users"
          subtitle="Highest-priority users ranked by weekly anomaly ratio and alert context"
          action={<span className="text-sm font-medium text-slate-500">{topUsers.length} users</span>}
        >
          <div className="space-y-3">
            {topUsers.length > 0 ? (
              topUsers.map((user) => (
                <Link
                  key={user.user_id}
                  to={`/user/${user.user_id}`}
                  className="block rounded-2xl border border-white/10 bg-white/[0.03] p-4 transition hover:border-cyan-400/20 hover:bg-white/[0.05]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{user.full_name}</p>
                      <p className="mt-1 text-sm text-slate-400">
                        {formatEmployeeId(user.employee_id)} • {user.department_name}
                      </p>
                    </div>
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-cyan-300">
                      {Math.round(user.anomaly_ratio)}% Ratio
                    </span>
                  </div>
                  <div className="mt-4 flex items-center justify-between text-sm">
                    <span className="text-slate-500">{user.anomalous_windows} / {user.total_windows} anomalous windows</span>
                    <span className="font-medium text-slate-200">{user.open_alert_count} open alerts</span>
                  </div>
                </Link>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-6 text-sm text-slate-500">
                No ranked users available yet.
              </div>
            )}
          </div>
        </SectionCard>

        <SectionCard
          title="Recent alerts across the organization"
          subtitle="Newest alert records from the stored dataset"
          action={<span className="text-sm font-medium text-slate-500">{recentAlerts.length} records</span>}
        >
          <div className="space-y-3">
            {recentAlerts.length > 0 ? (
              recentAlerts.map((alert) => (
                <div key={alert.alert_id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">
                        Alert #{alert.alert_id} for {alert.full_name}
                      </p>
                      <p className="mt-1 text-sm text-slate-400">
                        {formatEmployeeId(alert.employee_id)} • Created {formatRelativeTime(alert.created_at)}
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
                No organization alerts found.
              </div>
            )}
          </div>
        </SectionCard>
      </section>

      <SectionCard
        title="Department pulse"
        subtitle="Average risk and open-alert load by department"
        action={
          <span className="inline-flex items-center gap-2 text-sm text-slate-500">
            <CalendarClock size={16} />
            Org rollup
          </span>
        }
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {departmentRollup.length > 0 ? (
            departmentRollup.map((department) => (
              <div
                key={department.department_name}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 flex flex-col gap-2"
              >
                {/* Name row + badge */}
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-white leading-snug min-w-0 flex-1 break-words">{department.department_name}</p>
                  <span className="shrink-0 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider text-cyan-300 whitespace-nowrap">
                    {department.open_alert_count} Open
                  </span>
                </div>
                {/* Users count */}
                <p className="text-xs text-slate-400">{department.user_count} users monitored</p>
                {/* Avg risk — pinned to bottom with top border */}
                <p className="text-xs text-slate-500 mt-auto pt-2 border-t border-white/5">
                  Average risk <span className="font-semibold text-slate-300">{formatRisk(department.avg_risk)}</span>
                </p>
              </div>
            ))
          ) : (
            <div className="col-span-full rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-6 text-sm text-slate-500">
              No department summary found.
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
