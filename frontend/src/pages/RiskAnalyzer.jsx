import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, AlertOctagon, Activity, ShieldCheck, Loader2 } from 'lucide-react';
import { AnimatedNumber } from '@/components/ui/animated-number';
import { postAnalyzedEvent } from '@/services/api';
import { getRelativeTime } from '@/utils/time';

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function RiskAnalyzer() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [latestResult, setLatestResult] = useState(null);
  const [eventLogs, setEventLogs] = useState([]);

  // Form State matching the strict backend contract
  const [formData, setFormData] = useState({
    user_id: "user_123",
    timestamp: new Date().toISOString(),
    device_id: "device_abc",
    event_type: "Logon",
    current_logon_count: 1,
    current_logoff_count: 0,
    current_unique_pcs: 1,
    past_logins: "[]",
    logon_counts: "[]",
    unique_pcs_history: "[]",
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleAutoFillTime = () => {
    setFormData({ ...formData, timestamp: new Date().toISOString() });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        event: {
          user_id: formData.user_id,
          timestamp: formData.timestamp,
          device_id: formData.device_id,
          event_type: formData.event_type
        },
        user_history: {
          past_logins: JSON.parse(formData.past_logins),
          logon_counts: JSON.parse(formData.logon_counts),
          unique_pcs_history: JSON.parse(formData.unique_pcs_history),
          current_logon_count: Number(formData.current_logon_count),
          current_logoff_count: Number(formData.current_logoff_count),
          current_unique_pcs: Number(formData.current_unique_pcs)
        }
      };

      const response = await postAnalyzedEvent(payload);
      setLatestResult(response);
      
      const newLog = {
        id: Date.now(),
        timestamp: formData.timestamp,
        user_id: formData.user_id,
        anomaly_score: response.anomaly_score,
        aggregated_risk: response.aggregated_risk,
        risk_level: response.alert?.level || 'UNKNOWN',
        alert: response.alert?.alert || false,
      };

      setEventLogs(prev => [newLog, ...prev]);

    } catch (err) {
      setError(err.response?.data?.message || err.message || "An unexpected error occurred connecting to the backend.");
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level) => {
    if (level === 'HIGH') return 'text-accent-danger text-shadow-danger';
    if (level === 'MEDIUM') return 'text-accent-warning';
    if (level === 'LOW') return 'text-accent-safe';
    return 'text-muted-foreground';
  };

  const getRiskBg = (level) => {
    if (level === 'HIGH') return 'bg-accent-danger/10 border-accent-danger/30 shadow-glow-danger';
    if (level === 'MEDIUM') return 'bg-accent-warning/10 border-accent-warning/30 shadow-glow';
    if (level === 'LOW') return 'bg-accent-safe/10 border-accent-safe/30';
    return 'bg-white/5 border-white/10';
  };

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white drop-shadow-sm">Real-Time Risk Analyzer</h1>
          <p className="text-muted-foreground mt-2">Submit event data to the AI engine and visualize real-time risk calculations.</p>
        </div>
        <Badge variant="outline" className="border-primary/50 text-primary bg-primary/10">POST /event Stream Active</Badge>
      </motion.div>

      <div className="grid gap-6 xl:grid-cols-12">
        {/* Left Column: Form */}
        <motion.div variants={itemVariants} className="xl:col-span-5">
          <Card className="h-full bg-black/40 xl:sticky xl:top-24">
            <CardHeader>
              <CardTitle className="text-foreground/90">Event Submission Panel</CardTitle>
              <CardDescription>Input telemetry to stream directly to the backend engine.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-3">
                  <h3 className="text-xs font-bold tracking-widest text-primary uppercase">Event Details</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-foreground/80">User ID</label>
                      <input name="user_id" value={formData.user_id} onChange={handleChange} className="w-full h-9 bg-black/40 border border-white/10 rounded px-3 text-sm focus:ring-1 focus:ring-primary outline-none transition-colors" required />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-foreground/80">Event Type</label>
                      <input name="event_type" value={formData.event_type} onChange={handleChange} className="w-full h-9 bg-black/40 border border-white/10 rounded px-3 text-sm focus:ring-1 focus:ring-primary outline-none transition-colors" required />
                    </div>
                    <div className="space-y-1 col-span-2">
                       <label className="text-xs text-foreground/80 flex justify-between">
                         Timestamp (ISO)
                         <button type="button" onClick={handleAutoFillTime} className="text-primary hover:text-primary/80 transition-colors text-[10px]">Auto-fill now</button>
                       </label>
                      <input name="timestamp" value={formData.timestamp} onChange={handleChange} className="w-full h-9 bg-black/40 border border-white/10 rounded px-3 text-sm focus:ring-1 focus:ring-primary outline-none transition-colors" required />
                    </div>
                    <div className="space-y-1 col-span-2">
                      <label className="text-xs text-foreground/80">Device ID</label>
                      <input name="device_id" value={formData.device_id} onChange={handleChange} className="w-full h-9 bg-black/40 border border-white/10 rounded px-3 text-sm focus:ring-1 focus:ring-primary outline-none transition-colors" required />
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-4 border-t border-white/5">
                  <h3 className="text-xs font-bold tracking-widest text-primary uppercase">User History</h3>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-foreground/80" title="current_logon_count">Logon Cnt</label>
                      <input type="number" name="current_logon_count" value={formData.current_logon_count} onChange={handleChange} className="w-full h-9 bg-black/40 border border-white/10 rounded px-3 text-sm focus:ring-1 focus:ring-primary outline-none transition-colors" required />
                    </div>
                     <div className="space-y-1">
                      <label className="text-xs text-foreground/80" title="current_logoff_count">Logoff Cnt</label>
                      <input type="number" name="current_logoff_count" value={formData.current_logoff_count} onChange={handleChange} className="w-full h-9 bg-black/40 border border-white/10 rounded px-3 text-sm focus:ring-1 focus:ring-primary outline-none transition-colors" required />
                    </div>
                     <div className="space-y-1">
                      <label className="text-xs text-foreground/80" title="current_unique_pcs">Unq PCs</label>
                      <input type="number" name="current_unique_pcs" value={formData.current_unique_pcs} onChange={handleChange} className="w-full h-9 bg-black/40 border border-white/10 rounded px-3 text-sm focus:ring-1 focus:ring-primary outline-none transition-colors" required />
                    </div>
                  </div>
                   <div className="space-y-1">
                      <label className="text-xs text-foreground/80">Past Logins ([])</label>
                      <input name="past_logins" value={formData.past_logins} onChange={handleChange} className="w-full h-9 bg-black/60 border border-white/5 rounded px-3 text-sm font-mono text-muted-foreground focus:text-foreground focus:border-primary/50 outline-none transition-colors" />
                   </div>
                   <div className="space-y-1">
                      <label className="text-xs text-foreground/80">Logon Counts ([])</label>
                      <input name="logon_counts" value={formData.logon_counts} onChange={handleChange} className="w-full h-9 bg-black/60 border border-white/5 rounded px-3 text-sm font-mono text-muted-foreground focus:text-foreground focus:border-primary/50 outline-none transition-colors" />
                   </div>
                   <div className="space-y-1">
                      <label className="text-xs text-foreground/80">Unique PCs History ([])</label>
                      <input name="unique_pcs_history" value={formData.unique_pcs_history} onChange={handleChange} className="w-full h-9 bg-black/60 border border-white/5 rounded px-3 text-sm font-mono text-muted-foreground focus:text-foreground focus:border-primary/50 outline-none transition-colors" />
                   </div>
                </div>

                {error && (
                  <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="p-3 bg-destructive/20 border border-destructive/30 rounded text-destructive text-sm font-medium">
                    {error}
                  </motion.div>
                )}

                <Button type="submit" disabled={loading} className="w-full relative overflow-hidden group shadow-glow h-11 mt-4">
                  {loading ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin text-white" /> <span className="text-white">Analyzing Syntax...</span></>
                  ) : (
                    <><Play className="h-4 w-4 mr-2 relative z-10 text-white" /> <span className="relative z-10 font-bold text-white tracking-wide">POST /event</span></>
                  )}
                  {!loading && <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>}
                </Button>
              </form>
            </CardContent>
          </Card>
        </motion.div>

        {/* Right Column: Live Results */}
        <motion.div variants={itemVariants} className="xl:col-span-7 flex flex-col gap-6">
          {!latestResult ? (
            <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-white/10 rounded-xl bg-black/20 backdrop-blur min-h-[400px]">
              <Activity className="h-12 w-12 text-muted-foreground/30 mb-4" />
              <h2 className="text-xl font-semibold text-muted-foreground">Awaiting API Payload</h2>
              <p className="text-sm text-muted-foreground/50 max-w-sm text-center mt-2">Configure the payload on the left and submit it to receive the real-time aggregated risk analysis from the AI core.</p>
            </div>
          ) : (
            <>
              {/* Core UI: Risk Display */}
              <Card className={`relative overflow-hidden ${getRiskBg(latestResult.alert?.level)} transition-all duration-700`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                     <CardTitle className="text-sm font-medium uppercase tracking-widest opacity-80">Risk Assessment Result</CardTitle>
                     <span className="text-xs opacity-70 bg-black/20 px-2 py-1 rounded">User: {latestResult.alert?.user_id}</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between mt-2">
                     <div className="flex flex-col">
                       <span className="text-6xl font-black tracking-tighter drop-shadow-md pb-1">
                         <AnimatedNumber value={latestResult.aggregated_risk || 0} />
                       </span>
                       <span className="text-sm opacity-80 mt-1 uppercase tracking-wider font-semibold">Aggregated Risk</span>
                     </div>
                     <div className="flex flex-col items-end gap-3 translate-y-1">
                       {latestResult.alert?.alert ? (
                          <div className="flex items-center gap-2 bg-destructive text-white px-4 py-2 rounded-full font-bold shadow-glow-danger animate-pulse">
                            <AlertOctagon className="h-5 w-5" /> ACT ALERT TRIGGERED
                          </div>
                       ) : (
                          <div className="flex items-center gap-2 bg-accent-safe text-white px-4 py-2 rounded-full font-bold shadow-glow">
                            <ShieldCheck className="h-5 w-5" /> SYSTEM SECURE
                          </div>
                       )}
                       <div className="text-lg font-black uppercase tracking-wider">
                         Level: <span className={getRiskColor(latestResult.alert?.level)}>{latestResult.alert?.level}</span>
                       </div>
                     </div>
                  </div>
                </CardContent>
              </Card>

              {/* Score Breakdown */}
              <div className="grid grid-cols-2 gap-4">
                <Card className="bg-black/40 border-white/5 hover:border-white/10 transition-colors">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs tracking-widest text-muted-foreground uppercase">Anomaly Score</CardTitle>
                  </CardHeader>
                  <CardContent>
                     <div className="text-4xl font-bold text-white font-mono">
                        {(latestResult.anomaly_score || 0).toFixed(4)}
                     </div>
                  </CardContent>
                </Card>
                <Card className="bg-black/40 border-white/5 hover:border-white/10 transition-colors">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs tracking-widest text-muted-foreground uppercase">Aggregated Risk</CardTitle>
                  </CardHeader>
                  <CardContent>
                     <div className="text-4xl font-bold text-white font-mono">
                         {(latestResult.aggregated_risk || 0).toFixed(4)}
                     </div>
                  </CardContent>
                </Card>
              </div>

               {/* Event Log Table */}
               <Card className="flex-1 bg-black/40 border-white/5 overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between py-4 border-b border-white/5">
                  <CardTitle className="text-foreground/90 text-sm uppercase tracking-widest">Event Transmission Log</CardTitle>
                  <Badge variant="secondary" className="bg-white/5">{eventLogs.length} Events Logged</Badge>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="max-h-[350px] overflow-y-auto custom-scrollbar p-4 pt-0">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-white/5 hover:bg-transparent">
                          <TableHead className="text-xs whitespace-nowrap">Timestamp</TableHead>
                          <TableHead className="text-xs">User ID</TableHead>
                          <TableHead className="text-xs whitespace-nowrap">Anomaly</TableHead>
                          <TableHead className="text-xs whitespace-nowrap">Agg. Risk</TableHead>
                          <TableHead className="text-xs">Level</TableHead>
                          <TableHead className="text-xs text-right">Alert</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        <AnimatePresence initial={false}>
                          {eventLogs.map((log) => (
                            <motion.tr 
                              key={log.id}
                              layout
                              initial={{ opacity: 0, x: -10, backgroundColor: 'rgba(255,255,255,0.05)' }}
                              animate={{ opacity: 1, x: 0, backgroundColor: 'transparent' }}
                              transition={{ type: "spring", stiffness: 400, damping: 30 }}
                              className="border-white/5 hover:bg-white/5 transition-colors"
                            >
                              <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{new Date(log.timestamp).toLocaleTimeString()}</TableCell>
                              <TableCell className="text-xs text-white overflow-hidden text-ellipsis max-w-[80px]" title={log.user_id}>{log.user_id}</TableCell>
                              <TableCell className="text-xs font-mono">{Number(log.anomaly_score).toFixed(2)}</TableCell>
                              <TableCell className="text-xs font-mono">{Number(log.aggregated_risk).toFixed(2)}</TableCell>
                              <TableCell className="text-xs">
                                <Badge variant={log.risk_level === 'HIGH' ? 'danger' : log.risk_level === 'MEDIUM' ? 'warning' : 'success'} className="text-[10px] py-0">
                                  {log.risk_level}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-xs text-right">
                                {log.alert ? <span className="text-accent-danger font-bold">YES</span> : <span className="text-muted-foreground">NO</span>}
                              </TableCell>
                            </motion.tr>
                          ))}
                        </AnimatePresence>
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}
