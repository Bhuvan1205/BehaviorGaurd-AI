import { useEffect, useState, useMemo } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Mail,
  User,
  Search,
  BookOpen,
  Settings,
  Calendar,
  Layers,
  ChevronRight,
  RefreshCw,
  X,
  ArrowRight,
  ExternalLink,
  ChevronLeft
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  getAllEmailAnalyses,
  getEmailAnalysisBatches,
  getEmailPolicy,
  getUserEmailAnalysisEmails
} from "../services/api";

function formatTimestamp(value) {
  if (!value) return "N/A";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function EmailSecurityDashboard() {
  const [activeTab, setActiveTab] = useState("audits"); // 'audits' | 'policies'
  
  // Audits Tab State
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState("");
  const [analyses, setAnalyses] = useState([]);
  const [selectedVerdictFilter, setSelectedVerdictFilter] = useState("All");
  const [auditSearch, setAuditSearch] = useState("");
  const [isLoadingAudits, setIsLoadingAudits] = useState(false);
  
  // Policies Tab State
  const [rawPolicy, setRawPolicy] = useState("");
  const [policySearch, setPolicySearch] = useState("");
  const [selectedPolicySection, setSelectedPolicySection] = useState(0);
  const [isLoadingPolicy, setIsLoadingPolicy] = useState(false);

  // Detail Modal/Drawer State
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [flaggedEmails, setFlaggedEmails] = useState([]);
  const [isLoadingEmails, setIsLoadingEmails] = useState(false);

  // Load Initial Data
  useEffect(() => {
    const loadInitial = async () => {
      setIsLoadingAudits(true);
      try {
        const batchList = await getEmailAnalysisBatches();
        setBatches(batchList);
        if (batchList.length > 0) {
          setSelectedBatch(batchList[0]);
        }
      } catch (err) {
        console.error("Error loading email analysis batches:", err);
      } finally {
        setIsLoadingAudits(false);
      }
    };
    loadInitial();
  }, []);

  // Fetch Analyses when batch changes
  useEffect(() => {
    if (!selectedBatch) return;
    const fetchAnalyses = async () => {
      setIsLoadingAudits(true);
      try {
        const data = await getAllEmailAnalyses(selectedBatch);
        setAnalyses(data);
      } catch (err) {
        console.error("Error fetching email analyses:", err);
      } finally {
        setIsLoadingAudits(false);
      }
    };
    fetchAnalyses();
  }, [selectedBatch]);

  // Fetch Policy Document
  useEffect(() => {
    if (activeTab !== "policies" || rawPolicy) return;
    const fetchPolicy = async () => {
      setIsLoadingPolicy(true);
      try {
        const data = await getEmailPolicy();
        setRawPolicy(data.policy || "");
      } catch (err) {
        console.error("Error fetching policy document:", err);
      } finally {
        setIsLoadingPolicy(false);
      }
    };
    fetchPolicy();
  }, [activeTab, rawPolicy]);

  // Fetch Flagged Emails for selected user detail
  useEffect(() => {
    if (!activeAnalysis) {
      setFlaggedEmails([]);
      return;
    }
    const fetchEmails = async () => {
      setIsLoadingEmails(true);
      try {
        const emails = await getUserEmailAnalysisEmails(
          activeAnalysis.user_id,
          activeAnalysis.batch_date
        );
        setFlaggedEmails(emails);
      } catch (err) {
        console.error("Error loading flagged emails:", err);
      } finally {
        setIsLoadingEmails(false);
      }
    };
    fetchEmails();
  }, [activeAnalysis]);

  // Compute Stats for active batch
  const stats = useMemo(() => {
    const total = analyses.length;
    const flagged = analyses.filter((a) => a.verdict === "Flagged").length;
    const review = analyses.filter((a) => a.verdict === "Human Review Required").length;
    const normal = analyses.filter((a) => a.verdict === "Normal").length;
    return { total, flagged, review, normal };
  }, [analyses]);

  // Filtered analyses list
  const filteredAnalyses = useMemo(() => {
    return analyses.filter((a) => {
      const matchVerdict =
        selectedVerdictFilter === "All" || a.verdict === selectedVerdictFilter;
      const matchSearch =
        a.full_name.toLowerCase().includes(auditSearch.toLowerCase()) ||
        a.employee_id.toLowerCase().includes(auditSearch.toLowerCase()) ||
        a.department_name.toLowerCase().includes(auditSearch.toLowerCase());
      return matchVerdict && matchSearch;
    });
  }, [analyses, selectedVerdictFilter, auditSearch]);

  // Parse Policy Markdown into structured sections
  const policySections = useMemo(() => {
    if (!rawPolicy) return [];
    const lines = rawPolicy.split("\n");
    const sections = [];
    let currentTitle = "Overview & Scope";
    let currentContent = [];

    for (const line of lines) {
      const trimmed = line.trim();
      // Matches: ## 1. Purpose and Scope or ## Data Classification
      const match = trimmed.match(/^##\s+(?:\d+\.\s+)?(.*)$/);
      if (match) {
        if (currentTitle || currentContent.length > 0) {
          sections.push({
            title: currentTitle,
            content: currentContent.join("\n").trim(),
          });
        }
        currentTitle = match[1];
        currentContent = [];
      } else {
        // Avoid adding document main title again
        if (!trimmed.startsWith("# ")) {
          currentContent.push(line);
        }
      }
    }
    if (currentTitle || currentContent.length > 0) {
      sections.push({
        title: currentTitle,
        content: currentContent.join("\n").trim(),
      });
    }
    return sections;
  }, [rawPolicy]);

  // Filtered policy sections based on search
  const filteredPolicySections = useMemo(() => {
    if (!policySearch) return policySections;
    return policySections.filter(
      (sec) =>
        sec.title.toLowerCase().includes(policySearch.toLowerCase()) ||
        sec.content.toLowerCase().includes(policySearch.toLowerCase())
    );
  }, [policySections, policySearch]);

  // Highlight search text inside policy viewer
  const highlightText = (text, search) => {
    if (!search) return text;
    const parts = text.split(new RegExp(`(${search})`, "gi"));
    return parts.map((part, idx) =>
      part.toLowerCase() === search.toLowerCase() ? (
        <mark key={idx} className="bg-cyan-500/30 text-cyan-200 rounded px-1 py-0.5">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="space-y-6 pb-6">
      {/* Header Panel */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">
          Security Controls
        </p>
        <h1 className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white sm:text-4xl">
          <span className="inline-flex rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-cyan-300">
            <ShieldAlert size={24} />
          </span>
          Email Policy & RAG Audits
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400 sm:text-base">
          Dedicated security center matching weekly anomalous employee emails against corporate policies using dynamic Retrieval-Augmented Generation (RAG).
        </p>

        {/* Tab Selection */}
        <div className="mt-6 flex border-b border-white/10">
          <button
            onClick={() => setActiveTab("audits")}
            className={`flex items-center gap-2 border-b-2 px-6 py-3.5 text-sm font-semibold transition-all ${
              activeTab === "audits"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layers size={16} />
            Audit Center
          </button>
          <button
            onClick={() => setActiveTab("policies")}
            className={`flex items-center gap-2 border-b-2 px-6 py-3.5 text-sm font-semibold transition-all ${
              activeTab === "policies"
                ? "border-transparent text-slate-400 hover:text-slate-200"
                : "border-transparent text-slate-400"
            } ${
              activeTab === "policies" ? "border-cyan-400 text-cyan-300" : ""
            }`}
          >
            <BookOpen size={16} />
            Policy Documents
          </button>
        </div>
      </section>

      {activeTab === "audits" ? (
        <>
          {/* Audit Metrics */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-5 shadow-xl shadow-black/10">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Audited</span>
              <p className="mt-2 text-2xl font-bold text-white">
                {isLoadingAudits ? "..." : stats.total}
              </p>
              <p className="mt-1 text-xs text-slate-500">Top 5% Anomalous Employees</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-5 shadow-xl shadow-black/10">
              <span className="text-xs font-semibold uppercase tracking-wider text-rose-400">Flagged Insiders</span>
              <p className="mt-2 text-2xl font-bold text-rose-400">
                {isLoadingAudits ? "..." : stats.flagged}
              </p>
              <p className="mt-1 text-xs text-slate-500">High Risk Policy Violations</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-5 shadow-xl shadow-black/10">
              <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">Human Reviews</span>
              <p className="mt-2 text-2xl font-bold text-amber-400">
                {isLoadingAudits ? "..." : stats.review}
              </p>
              <p className="mt-1 text-xs text-slate-500">Inconclusive Indicators</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-5 shadow-xl shadow-black/10">
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Normal / Safe</span>
              <p className="mt-2 text-2xl font-bold text-emerald-400">
                {isLoadingAudits ? "..." : stats.normal}
              </p>
              <p className="mt-1 text-xs text-slate-500">No Violations Found</p>
            </div>
          </section>

          {/* Audit Controls & Filters */}
          <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20 space-y-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              {/* Batch & Search */}
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-400 whitespace-nowrap">Audit Batch:</span>
                  <select
                    value={selectedBatch}
                    onChange={(e) => setSelectedBatch(e.target.value)}
                    disabled={isLoadingAudits}
                    className="rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-400 disabled:opacity-55"
                  >
                    {batches.map((b) => (
                      <option key={b} value={b}>
                        {b}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="relative flex-1 sm:w-64">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                  <input
                    type="text"
                    placeholder="Search name, ID, department..."
                    value={auditSearch}
                    onChange={(e) => setAuditSearch(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-slate-900/50 py-2 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
                  />
                </div>
              </div>

              {/* Verdict Filter Tabs */}
              <div className="flex flex-wrap gap-1.5 rounded-xl bg-slate-900/50 p-1 border border-white/5">
                {["All", "Flagged", "Human Review Required", "Normal"].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setSelectedVerdictFilter(tab)}
                    className={`rounded-lg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider transition ${
                      selectedVerdictFilter === tab
                        ? "bg-cyan-500/10 text-cyan-300 border border-cyan-400/20"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            {/* Audits Table */}
            {isLoadingAudits ? (
              <div className="py-20 text-center text-slate-500 space-y-3">
                <RefreshCw size={28} className="animate-spin mx-auto text-cyan-400" />
                <p className="text-sm">Fetching audit records...</p>
              </div>
            ) : filteredAnalyses.length === 0 ? (
              <div className="py-20 text-center border border-dashed border-white/10 rounded-2xl bg-white/[0.01]">
                <p className="text-sm text-slate-400">No email audits found matching your filters.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-950/40">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="bg-white/[0.03] text-xs uppercase tracking-[0.1em] text-slate-400">
                    <tr>
                      <th className="p-4">Employee</th>
                      <th className="p-4">Department & Role</th>
                      <th className="p-4">Verdict</th>
                      <th className="p-4">Policies Violated</th>
                      <th className="p-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {filteredAnalyses.map((analysis) => (
                      <tr key={analysis.analysis_id} className="hover:bg-white/[0.01] transition-colors">
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <span className="rounded-xl bg-slate-900 border border-white/10 p-2.5 text-slate-300">
                              <User size={16} />
                            </span>
                            <div>
                              <p className="font-semibold text-white">{analysis.full_name}</p>
                              <p className="text-xs text-slate-500">{analysis.employee_id}</p>
                            </div>
                          </div>
                        </td>
                        <td className="p-4">
                          <p className="text-slate-300 font-medium">{analysis.department_name}</p>
                          <p className="text-xs text-slate-500">{analysis.role_name}</p>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-wider ${
                            analysis.verdict === "Flagged"
                              ? "border-rose-500/20 bg-rose-500/10 text-rose-400"
                              : analysis.verdict === "Human Review Required"
                              ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
                              : "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                          }`}>
                            {analysis.verdict}
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {analysis.policy_sections_used && analysis.policy_sections_used.length > 0 ? (
                              analysis.policy_sections_used.map((sec) => (
                                <span key={sec} className="rounded-md bg-white/[0.04] border border-white/5 px-2 py-0.5 text-xs text-slate-400">
                                  {sec}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-slate-500">—</span>
                            )}
                          </div>
                        </td>
                        <td className="p-4 text-right">
                          <button
                            onClick={() => setActiveAnalysis(analysis)}
                            className="rounded-xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-400/15"
                          >
                            View Analysis
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : (
        /* Policies Tab */
        <section className="grid gap-6 lg:grid-cols-[280px_1fr] items-start">
          {/* TOC Sidebar */}
          <div className="rounded-[1.6rem] border border-white/10 bg-slate-950/70 p-4 shadow-xl space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
              <input
                type="text"
                placeholder="Search policy content..."
                value={policySearch}
                onChange={(e) => setPolicySearch(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-slate-900/50 py-2 pl-8 pr-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-400"
              />
            </div>

            {isLoadingPolicy ? (
              <div className="py-10 text-center text-xs text-slate-500">Loading TOC...</div>
            ) : (
              <nav className="space-y-1 max-h-[400px] overflow-y-auto pr-1">
                {filteredPolicySections.map((sec, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedPolicySection(idx)}
                    className={`w-full text-left rounded-xl px-3.5 py-2.5 text-xs font-medium transition ${
                      selectedPolicySection === idx
                        ? "bg-cyan-500/10 text-cyan-300 border border-cyan-400/20"
                        : "text-slate-400 hover:bg-white/[0.03] hover:text-slate-200"
                    }`}
                  >
                    {sec.title}
                  </button>
                ))}
                {filteredPolicySections.length === 0 && (
                  <p className="text-center text-xs text-slate-500 py-4">No sections match search.</p>
                )}
              </nav>
            )}
          </div>

          {/* Reading Pane */}
          <div className="rounded-[1.9rem] border border-white/10 bg-slate-950/70 p-6 shadow-xl min-h-[400px]">
            {isLoadingPolicy ? (
              <div className="py-24 text-center text-slate-500 space-y-3">
                <RefreshCw size={28} className="animate-spin mx-auto text-cyan-400" />
                <p className="text-sm">Loading security policy documents...</p>
              </div>
            ) : filteredPolicySections[selectedPolicySection] ? (
              <article className="space-y-6">
                {/* Header */}
                <div className="border-b border-white/10 pb-4">
                  <h2 className="text-xl font-bold text-white">
                    {filteredPolicySections[selectedPolicySection].title}
                  </h2>
                </div>

                {/* Content */}
                <div className="text-sm text-slate-300 leading-relaxed space-y-4 whitespace-pre-line">
                  {highlightText(
                    filteredPolicySections[selectedPolicySection].content,
                    policySearch
                  )}
                </div>
              </article>
            ) : (
              <div className="py-24 text-center text-slate-500">
                <p className="text-sm">No policy document content available.</p>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Detail Modal/Drawer */}
      {activeAnalysis && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-sm">
          <div className="h-full w-full max-w-3xl border-l border-white/10 bg-slate-950 p-6 shadow-2xl overflow-y-auto space-y-6 flex flex-col justify-between">
            <div className="space-y-6">
              {/* Modal Header */}
              <div className="flex items-start justify-between border-b border-white/10 pb-4">
                <div>
                  <h2 className="text-xl font-bold text-white">{activeAnalysis.full_name}</h2>
                  <p className="text-sm text-slate-400">
                    ID: {activeAnalysis.employee_id} • {activeAnalysis.department_name} • {activeAnalysis.role_name}
                  </p>
                </div>
                <button
                  onClick={() => setActiveAnalysis(null)}
                  className="rounded-full border border-white/10 bg-white/[0.04] p-1.5 text-slate-400 hover:text-slate-100 transition"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Assessment Panel */}
              <div className="grid gap-4 sm:grid-cols-[160px_1fr]">
                {/* Verdict Indicator */}
                <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 flex flex-col items-center justify-center text-center">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">RAG Verdict</span>
                  <span className={`mt-2 rounded-full border px-3.5 py-1 text-xs font-bold uppercase tracking-wider ${
                    activeAnalysis.verdict === "Flagged"
                      ? "border-rose-500/20 bg-rose-500/10 text-rose-400"
                      : activeAnalysis.verdict === "Human Review Required"
                      ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
                      : "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                  }`}>
                    {activeAnalysis.verdict}
                  </span>
                  <span className="mt-4 text-[10px] text-slate-500">
                    Audited: {formatTimestamp(activeAnalysis.created_at)}
                  </span>
                </div>

                {/* Explanation text */}
                <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5 space-y-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">AI Assessment Explanation</span>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {activeAnalysis.explanation}
                  </p>
                  
                  {activeAnalysis.policy_sections_used && activeAnalysis.policy_sections_used.length > 0 && (
                    <div className="pt-2 flex flex-wrap items-center gap-1.5">
                      <span className="text-xs text-slate-500">Policies Referenced:</span>
                      {activeAnalysis.policy_sections_used.map((sec) => (
                        <span key={sec} className="rounded-md bg-white/[0.05] border border-white/5 px-2 py-0.5 text-xs text-slate-400">
                          {sec}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Flagged Emails Table */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Mail size={16} className="text-cyan-400" />
                  Flagged Emails in Anomalous Hours
                </h3>

                {isLoadingEmails ? (
                  <div className="py-8 text-center text-slate-500 text-sm">Loading emails...</div>
                ) : flaggedEmails.length === 0 ? (
                  <div className="rounded-xl border border-white/5 bg-white/[0.01] p-6 text-center text-sm text-slate-500">
                    No flagged emails matching the exfiltration filter were detected in anomalous windows.
                  </div>
                ) : (
                  <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-950/40">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="bg-white/[0.03] uppercase tracking-wider text-slate-400">
                        <tr>
                          <th className="p-3">Date/Time</th>
                          <th className="p-3">Recipient</th>
                          <th className="p-3">Subject</th>
                          <th className="p-3">Attachments</th>
                          <th className="p-3">Risk Category</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {flaggedEmails.map((email) => (
                          <tr key={email.id} className="hover:bg-white/[0.01]">
                            <td className="p-3 whitespace-nowrap text-slate-400">
                              {formatTimestamp(email.email_date)}
                            </td>
                            <td className="p-3 text-cyan-400 font-medium">{email.recipient_to}</td>
                            <td className="p-3 font-semibold text-white">{email.subject}</td>
                            <td className="p-3 text-slate-400">{email.attachment_count} files</td>
                            <td className="p-3">
                              <span className={`rounded px-1.5 py-0.5 font-semibold ${
                                email.external_recipient
                                  ? "bg-rose-950/40 text-rose-300 border border-rose-500/10"
                                  : "bg-slate-900 text-slate-300"
                              }`}>
                                {email.external_recipient ? "External Exfil" : "Internal Check"}
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

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-3 border-t border-white/10 pt-4 mt-6">
              <button
                onClick={() => setActiveAnalysis(null)}
                className="rounded-xl border border-white/10 bg-white/[0.04] px-5 py-2.5 text-sm font-semibold text-slate-300 transition hover:bg-white/[0.07]"
              >
                Close
              </button>
              <Link
                to={`/user/${activeAnalysis.user_id}`}
                onClick={() => setActiveAnalysis(null)}
                className="inline-flex items-center gap-2 rounded-xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-2.5 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-400/15"
              >
                Go to Full User Analytics
                <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
