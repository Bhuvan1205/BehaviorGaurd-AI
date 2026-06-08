import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarClock,
  Mail,
  ShieldUser,
  TriangleAlert,
  UserRound,
  CheckCircle,
  Loader2,
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
import { getAlerts, getHistory, getUserDetail, getUserEmailAnalyses, getUserEmailAnalysisEmails } from "../services/api";
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
  const [weeklyTrends, setWeeklyTrends] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [emailAnalyses, setEmailAnalyses] = useState([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [selectedAnalysisEmails, setSelectedAnalysisEmails] = useState([]);
  const [isEmailsLoading, setIsEmailsLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!effectiveUserId) {
      setUser(null);
      setHistory([]);
      setWeeklyTrends([]);
      setAlerts([]);
      setEmailAnalyses([]);
      setSelectedAnalysis(null);
      setIsLoading(false);
      return;
    }

    selectUser(effectiveUserId);
    let isMounted = true;

    const loadUser = async () => {
      setIsLoading(true);
      setError("");

      try {
        const [userData, historyData, alertsData, emailAnalysesData] = await Promise.all([
          getUserDetail(effectiveUserId),
          getHistory(effectiveUserId),
          getAlerts(effectiveUserId),
          getUserEmailAnalyses(effectiveUserId),
        ]);

        if (!isMounted) {
          return;
        }

        setUser(userData);
        setHistory(Array.isArray(historyData?.windows) ? historyData.windows : []);
        setWeeklyTrends(Array.isArray(historyData?.weekly_trends) ? historyData.weekly_trends : []);
        setAlerts(Array.isArray(alertsData) ? alertsData : []);
        
        const analyses = Array.isArray(emailAnalysesData) ? emailAnalysesData : [];
        setEmailAnalyses(analyses);
        if (analyses.length > 0) {
          setSelectedAnalysis(analyses[0]);
        } else {
          setSelectedAnalysis(null);
        }
      } catch (requestError) {
        if (isMounted) {
          setError(requestError.message || "Unable to load user detail.");
          setUser(null);
          setHistory([]);
          setWeeklyTrends([]);
          setAlerts([]);
          setEmailAnalyses([]);
          setSelectedAnalysis(null);
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

  // Effect to load emails when selected RAG analysis batch changes
  useEffect(() => {
    if (!effectiveUserId || !selectedAnalysis?.batch_date) {
      setSelectedAnalysisEmails([]);
      return;
    }

    let isMounted = true;
    const loadFlaggedEmails = async () => {
      setIsEmailsLoading(true);
      try {
        const emails = await getUserEmailAnalysisEmails(effectiveUserId, selectedAnalysis.batch_date);
        if (isMounted) {
          setSelectedAnalysisEmails(emails);
        }
      } catch (err) {
        console.error("Error loading RAG emails:", err);
      } finally {
        if (isMounted) {
          setIsEmailsLoading(false);
        }
      }
    };

    loadFlaggedEmails();

    return () => {
      isMounted = false;
    };
  }, [effectiveUserId, selectedAnalysis?.batch_date]);

  const anomalyTrendData = useMemo(
    () =>
      weeklyTrends.map((item) => ({
        label: item.batch_date,
        rate: Number(item.anomaly_rate || 0),
        batch_date: item.batch_date,
      })),
    [weeklyTrends]
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
          <p className="text-sm font-medium text-slate-400">Weekly anomaly rate</p>
          <p className="mt-3 text-2xl font-semibold text-white">{Math.round(user.latest_anomaly_rate || 0)}%</p>
          <p className="mt-4 text-sm text-slate-500">
            {user.latest_anomaly_count} / {user.latest_total_windows} windows anomalous
          </p>
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

      {/* Email Security Audit (RAG) section */}
      <section className="rounded-[1.9rem] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Email Security Audit (RAG)</h2>
            <p className="mt-1 text-sm text-slate-400">
              RAG-based security policy analysis run on top 5% anomalous users.
            </p>
          </div>
          {emailAnalyses.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400">Select Batch:</span>
              <select
                value={selectedAnalysis?.batch_date || ""}
                onChange={(e) => {
                  const found = emailAnalyses.find((a) => a.batch_date === e.target.value);
                  if (found) setSelectedAnalysis(found);
                }}
                className="rounded-xl border border-white/10 bg-slate-900/80 p-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-400"
              >
                {emailAnalyses.map((a) => (
                  <option key={a.batch_date} value={a.batch_date}>
                    {a.batch_date}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {emailAnalyses.length === 0 ? (
          <div className="flex h-40 items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] text-sm text-slate-500">
            No email security audit records found for this user.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Verdict and Explanation */}
            <div className="grid gap-6 md:grid-cols-[1fr_2.5fr]">
              {/* Verdict Card */}
              <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5 flex flex-col items-center justify-center text-center">
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  RAG Verdict
                </span>
                <span className={`mt-3 rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-[0.16em] ${
                  selectedAnalysis?.verdict === "Flagged"
                    ? "border-rose-500/20 bg-rose-500/10 text-rose-400"
                    : selectedAnalysis?.verdict === "Human Review Required"
                    ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
                    : "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                }`}>
                  {selectedAnalysis?.verdict}
                </span>
                <span className="mt-4 text-xs text-slate-500">
                  Audited: {formatTimestamp(selectedAnalysis?.created_at)}
                </span>
              </div>

              {/* Explanation Card */}
              <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5 space-y-3">
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  AI Security Assessment
                </span>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {selectedAnalysis?.explanation}
                </p>
                {selectedAnalysis?.policy_sections_used && selectedAnalysis.policy_sections_used.length > 0 && (
                  <div className="pt-2 flex flex-wrap items-center gap-2">
                    <span className="text-xs text-slate-500 mr-1">Policy Referenced:</span>
                    {selectedAnalysis.policy_sections_used.map((sec) => (
                      <span key={sec} className="rounded-lg bg-white/[0.05] px-2.5 py-1 text-xs text-slate-400 border border-white/5">
                        {sec}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Flagged Emails Table */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-white">Flagged Emails in Anomalous Windows</h3>
              {isEmailsLoading ? (
                <div className="py-8 text-center text-slate-500 text-sm">
                  Loading flagged emails...
                </div>
              ) : selectedAnalysisEmails.length === 0 ? (
                <div className="rounded-2xl border border-white/5 bg-white/[0.01] p-6 text-center text-sm text-slate-500">
                  No flagged emails associated with this audit run.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-950/40">
                  <table className="w-full text-left text-sm text-slate-300">
                    <thead className="bg-white/[0.03] text-xs uppercase tracking-[0.1em] text-slate-400">
                      <tr>
                        <th className="p-4">Date/Time</th>
                        <th className="p-4">Recipient</th>
                        <th className="p-4">Subject</th>
                        <th className="p-4">Attachments</th>
                        <th className="p-4">Risk Level</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {selectedAnalysisEmails.map((email) => (
                        <tr key={email.id} className="hover:bg-white/[0.01] transition-colors">
                          <td className="p-4 whitespace-nowrap text-slate-400">
                            {formatTimestamp(email.email_date)}
                          </td>
                          <td className="p-4 text-cyan-400 font-medium">
                            {email.recipient_to}
                          </td>
                          <td className="p-4 font-semibold text-white">
                            {email.subject}
                          </td>
                          <td className="p-4 text-slate-400">
                            {email.attachment_count} files
                          </td>
                          <td className="p-4">
                            <span className={`rounded-lg px-2 py-0.5 text-xs font-semibold ${
                              email.external_recipient 
                                ? "bg-rose-950/50 text-rose-300 border border-rose-500/20" 
                                : "bg-slate-900 text-slate-300"
                            }`}>
                              {email.external_recipient ? "External Exfil Risk" : "Internal Policy Check"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <SectionCard
          title="Weekly anomaly trend"
          subtitle="How this user's weekly anomaly rate has moved over previous weeks"
          action={
            <span className="inline-flex items-center gap-2 text-sm text-slate-500">
              <CalendarClock size={16} />
              {weeklyTrends.length} weeks
            </span>
          }
        >
          {anomalyTrendData.length > 0 ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={anomalyTrendData}>
                  <defs>
                    <linearGradient id="userRiskTrend" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                      <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis
                    domain={[0, 'auto']}
                    tickFormatter={(value) => `${Math.round(value)}%`}
                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    width={44}
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
                  <Area type="monotone" dataKey="rate" stroke="#22d3ee" strokeWidth={3} fill="url(#userRiskTrend)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-80 items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] text-sm text-slate-500">
              No user anomaly history available yet.
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
              Weekly anomaly rate is <span className="font-semibold text-white">{Math.round(user.latest_anomaly_rate || 0)}%</span>.
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
            <p><span className="text-slate-500">Weekly anomaly rate:</span> {Math.round(user.latest_anomaly_rate || 0)}%</p>
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
