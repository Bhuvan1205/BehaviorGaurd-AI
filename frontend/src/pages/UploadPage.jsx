import { useState, useEffect } from "react";
import { 
  CloudUpload, 
  FileSpreadsheet, 
  CheckCircle, 
  XCircle, 
  Loader2, 
  Calendar,
  AlertTriangle,
  Play
} from "lucide-react";
import { Link } from "react-router-dom";
import { uploadLog, getJobStatus, uploadEmails } from "../services/api";

export function UploadPage() {
  const [file, setFile] = useState(null);
  const [emailFile, setEmailFile] = useState(null);
  const [batchDate, setBatchDate] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isEmailUploading, setIsEmailUploading] = useState(false);
  const [emailUploadSuccess, setEmailUploadSuccess] = useState("");
  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState(null);
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  // Poll status of the batch job every 2 seconds if it's queued or running
  useEffect(() => {
    if (!jobId || !["queued", "running"].includes(jobStatus?.status)) {
      return;
    }

    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const status = await getJobStatus(jobId);
        if (isMounted) {
          setJobStatus(status);
        }
      } catch (err) {
        console.error("Error polling job status:", err);
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [jobId, jobStatus?.status]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      const ext = droppedFile.name.split(".").pop().toLowerCase();
      if (["csv", "xlsx", "xls"].includes(ext)) {
        setFile(droppedFile);
        setError("");
      } else {
        setError("Invalid file format. Please upload a CSV or Excel file.");
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError("");
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a behavior logs file to upload.");
      return;
    }
    if (!batchDate) {
      setError("Please select a batch date.");
      return;
    }

    setIsUploading(true);
    setError("");
    setJobStatus(null);
    setJobId("");
    setEmailUploadSuccess("");

    try {
      // 1. If email file is selected, upload it first
      if (emailFile) {
        setIsEmailUploading(true);
        const emailRes = await uploadEmails(emailFile);
        setIsEmailUploading(false);
        setEmailUploadSuccess(
          `Successfully ingested ${emailRes.ingested_rows} email events.`
        );
      }

      // 2. Upload behavior logs and queue ML job
      const res = await uploadLog(file, batchDate);
      setJobId(res.job_id);
      setJobStatus({ status: "queued", message: "Job successfully queued" });
    } catch (err) {
      setError(err.message || "Ingestion job failed. Please try again.");
    } finally {
      setIsUploading(false);
      setIsEmailUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setEmailFile(null);
    setBatchDate("");
    setJobId("");
    setJobStatus(null);
    setError("");
    setEmailUploadSuccess("");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/20 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">Data Center</p>
        <h1 className="mt-3 flex items-center gap-3 text-3xl font-semibold text-white sm:text-4xl">
          <span className="inline-flex rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-cyan-300">
            <CloudUpload size={24} />
          </span>
          Weekly Ingestion Pipeline
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
          Upload weekly logon logs (CSV or Excel) to run the V6 behavioral anomaly detection pipeline. The pipeline segments users by context, computes deviation features, runs HDBSCAN density clustering, and checks Isolation Forest scores.
        </p>
      </section>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Form Card */}
        <section className="rounded-[1.9rem] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <h2 className="text-lg font-semibold text-white">Upload New Batch</h2>
          <p className="mt-1 text-sm text-slate-400">Specify the batch date and drag in your data file.</p>

          <form onSubmit={handleUpload} className="mt-6 space-y-5">
            {/* Date Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Calendar size={16} className="text-cyan-400" />
                Batch Date (Week Ending Date)
              </label>
              <input 
                type="date" 
                value={batchDate}
                onChange={(e) => setBatchDate(e.target.value)}
                disabled={isUploading || !!jobId}
                className="w-full rounded-2xl border border-white/10 bg-slate-900/50 p-3.5 text-sm text-white focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 disabled:opacity-50"
              />
            </div>

            {/* Drag and Drop Zone */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Logs Dataset (CSV or Excel)</label>
              
              {!file ? (
                <div 
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  className={`flex flex-col items-center justify-center rounded-2xl border border-dashed p-8 transition-colors ${
                    dragActive 
                      ? "border-cyan-400 bg-cyan-400/5" 
                      : "border-white/10 bg-slate-900/20 hover:border-white/20 hover:bg-slate-900/30"
                  }`}
                >
                  <CloudUpload size={40} className="text-slate-400 group-hover:text-cyan-300" />
                  <p className="mt-3 text-sm text-slate-300">
                    Drag and drop your file here, or{" "}
                    <label className="cursor-pointer text-cyan-400 hover:underline">
                      browse
                      <input 
                        type="file" 
                        accept=".csv,.xlsx,.xls"
                        onChange={handleFileChange}
                        className="hidden" 
                      />
                    </label>
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Supports CSV, XLSX, and XLS formats</p>
                </div>
              ) : (
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-900/50 p-4">
                  <div className="flex items-center gap-3">
                    <span className="rounded-xl border border-cyan-400/20 bg-cyan-400/10 p-2.5 text-cyan-300">
                      <FileSpreadsheet size={20} />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-white">{file.name}</p>
                      <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                  {!jobId && (
                    <button 
                      type="button"
                      onClick={() => setFile(null)}
                      className="text-xs text-slate-400 hover:text-rose-400 transition"
                    >
                      Remove
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Email Logs File Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Email Logs Dataset (CSV or Excel) (Optional)</label>
              
              {!emailFile ? (
                <div className="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-slate-900/20 hover:border-white/20 hover:bg-slate-900/30 p-6 transition-colors">
                  <p className="text-sm text-slate-300">
                    <label className="cursor-pointer text-cyan-400 hover:underline">
                      Select Email CSV File
                      <input 
                        type="file" 
                        accept=".csv,.xlsx,.xls"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setEmailFile(e.target.files[0]);
                          }
                        }}
                        disabled={isUploading || !!jobId}
                        className="hidden" 
                      />
                    </label>
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Supports CSV, XLSX, and XLS formats</p>
                </div>
              ) : (
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-900/50 p-4">
                  <div className="flex items-center gap-3">
                    <span className="rounded-xl border border-cyan-400/20 bg-cyan-400/10 p-2.5 text-cyan-300">
                      <FileSpreadsheet size={20} />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-white">{emailFile.name}</p>
                      <p className="text-xs text-slate-500">{(emailFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                  {!jobId && (
                    <button 
                      type="button"
                      onClick={() => setEmailFile(null)}
                      className="text-xs text-slate-400 hover:text-rose-400 transition"
                    >
                      Remove
                    </button>
                  )}
                </div>
              )}
            </div>

            {emailUploadSuccess && (
              <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm text-emerald-200 flex items-start gap-2.5">
                <CheckCircle size={16} className="shrink-0 mt-0.5 text-emerald-400" />
                <span>{emailUploadSuccess}</span>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200 flex items-start gap-2.5">
                <AlertTriangle size={16} className="shrink-0 mt-0.5 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            {/* Actions */}
            {!jobId ? (
              <button 
                type="submit"
                disabled={isUploading || !file || !batchDate}
                className="w-full flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3.5 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-400/15 disabled:opacity-50"
              >
                {isUploading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Uploading file...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Start Ingestion Job
                  </>
                )}
              </button>
            ) : (
              <button 
                type="button"
                onClick={handleReset}
                className="w-full rounded-2xl border border-white/10 bg-white/[0.04] p-3.5 text-sm font-semibold text-slate-300 transition hover:bg-white/[0.07]"
              >
                Reset Form
              </button>
            )}
          </form>
        </section>

        {/* Pipeline Monitor Card */}
        <section className="rounded-[1.9rem] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20 flex flex-col">
          <h2 className="text-lg font-semibold text-white">Pipeline Monitor</h2>
          <p className="mt-1 text-sm text-slate-400">Track the execution of the batch processing job.</p>

          <div className="flex-1 mt-6 flex flex-col justify-center min-h-[300px]">
            {!jobId ? (
              <div className="text-center p-8 text-slate-500">
                <Loader2 size={32} className="mx-auto text-slate-600 opacity-50 mb-3" />
                <p className="text-sm">No active pipeline jobs to monitor.</p>
                <p className="text-xs mt-1">Configure and start a batch upload to initiate tracking.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Stepper Status Indicator */}
                <div className="relative flex items-center justify-between px-6">
                  {/* Progress Line */}
                  <div className="absolute left-10 right-10 top-1/2 h-0.5 -translate-y-1/2 bg-white/10 z-0"></div>
                  
                  {/* Status Steps */}
                  {[
                    { label: "Queued", statusVal: "queued" },
                    { label: "Running", statusVal: "running" },
                    { label: "Done", statusVal: "complete" }
                  ].map((step, idx) => {
                    const isPassed = 
                      jobStatus?.status === "complete" ||
                      (step.statusVal === "queued" && ["queued", "running"].includes(jobStatus?.status)) ||
                      (step.statusVal === "running" && jobStatus?.status === "running");

                    const isActive = jobStatus?.status === step.statusVal;
                    const isFailed = jobStatus?.status === "failed";

                    return (
                      <div key={step.label} className="relative z-10 flex flex-col items-center">
                        <div className={`flex h-9 w-9 items-center justify-center rounded-full border transition-all duration-300 ${
                          isFailed && idx === 2
                            ? "border-rose-400 bg-rose-950 text-rose-300"
                            : isPassed
                            ? "border-cyan-400 bg-cyan-950 text-cyan-300"
                            : isActive
                            ? "border-cyan-400 bg-cyan-950 text-cyan-300"
                            : "border-white/10 bg-slate-900 text-slate-500"
                        }`}>
                          {isActive ? (
                            <Loader2 size={16} className="animate-spin" />
                          ) : isFailed && idx === 2 ? (
                            <XCircle size={16} />
                          ) : isPassed ? (
                            <CheckCircle size={16} />
                          ) : (
                            <span className="text-xs font-semibold">{idx + 1}</span>
                          )}
                        </div>
                        <span className={`mt-2 text-xs font-medium ${
                          isActive ? "text-cyan-300" : isPassed ? "text-slate-300" : "text-slate-500"
                        }`}>
                          {step.label}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Job Info Message */}
                <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-5 space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">Job ID:</span>
                    <span className="font-mono text-xs text-slate-300">{jobId}</span>
                  </div>
                  
                  {jobStatus?.status === "failed" ? (
                    <div className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-300 flex items-start gap-2.5">
                      <XCircle size={16} className="shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold">Pipeline Error</p>
                        <p className="text-xs mt-0.5">{jobStatus.error || "Execution terminated unexpectedly."}</p>
                      </div>
                    </div>
                  ) : jobStatus?.status === "complete" ? (
                    <div className="space-y-3">
                      <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-3 text-sm text-emerald-300 flex items-center gap-2.5">
                        <CheckCircle size={16} className="shrink-0" />
                        <span className="font-semibold">Processing Complete!</span>
                      </div>

                      {jobStatus.summary && (
                        <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
                          <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-center">
                            <p className="text-slate-500 font-medium">Scored Windows</p>
                            <p className="text-lg font-bold text-white mt-1">
                              {Number(jobStatus.summary.total_records || 0).toLocaleString()}
                            </p>
                          </div>
                          <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-center">
                            <p className="text-slate-500 font-medium">Employees Scored</p>
                            <p className="text-lg font-bold text-white mt-1">
                              {Number(jobStatus.summary.total_users || 0).toLocaleString()}
                            </p>
                          </div>
                          <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-center">
                            <p className="text-slate-500 font-medium">Anomalies Detected</p>
                            <p className="text-lg font-bold text-rose-400 mt-1">
                              {Number(jobStatus.summary.anomalies_detected || 0).toLocaleString()}
                            </p>
                          </div>
                          <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-center">
                            <p className="text-slate-500 font-medium">Alerts Generated</p>
                            <p className="text-lg font-bold text-amber-300 mt-1">
                              {Number(jobStatus.summary.alerts_generated || 0).toLocaleString()}
                            </p>
                          </div>
                          
                          {jobStatus.summary.email_audits_status === "complete" && (
                            <div className="col-span-2 rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-3 text-center">
                              <p className="text-cyan-400 font-medium text-xs font-semibold uppercase tracking-wider">Policy RAG Audits Completed</p>
                              <p className="text-sm font-bold text-white mt-1">
                                {Number(jobStatus.summary.email_audited_count || 0)} employees audited
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      <Link 
                        to="/alerts"
                        className="w-full flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3.5 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-400/15"
                      >
                        Go to Threat Dashboard
                      </Link>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <Loader2 className="animate-spin text-cyan-400 mx-auto mb-2" size={20} />
                      <p className="text-sm text-slate-300">
                        {jobStatus?.status === "running" ? "Analyzing log features..." : "Queuing log file..."}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
