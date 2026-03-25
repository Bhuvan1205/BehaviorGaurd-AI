import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Clock, ShieldAlert } from 'lucide-react';
import { useRealTime } from '@/context/RealTimeContext';
import { motion } from 'framer-motion';
import { AnimatedNumber } from '@/components/ui/animated-number';
import { getRelativeTime } from '@/utils/time';

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};
const itemVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { opacity: 1, scale: 1, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function UserDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { users, alerts: allAlerts } = useRealTime();

  const user = users.find(u => u.id === parseInt(id));
  const alerts = allAlerts.filter(a => a.userId === parseInt(id));

  // Static mock timeline for demonstration, injected with "just now" for top entry
  const timeline = [
    { id: 1, action: "Logged in", timestamp: user?.lastActivity || Date.now() },
    { id: 2, action: "Downloaded file", timestamp: Date.now() - 3600000 }
  ];

  if (!user) return <div className="p-8 text-center text-muted-foreground">Loading details...</div>;

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariants} className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)} className="hover:bg-white/5">
          <ArrowLeft className="h-5 w-5 text-muted-foreground hover:text-white" />
        </Button>
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-white drop-shadow-sm">User: {user.username}</h1>
           <p className="text-muted-foreground mt-1">Live shifting behavioral profile</p>
        </div>
      </motion.div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <motion.div variants={itemVariants}>
          <Card className="h-full relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <CardHeader>
              <CardTitle>Live Risk Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center p-6 space-y-4">
                <div className="text-6xl font-black shrink-0 tracking-tighter drop-shadow-glow transition-all">
                  <span className={user.riskScore > 75 ? "text-accent-danger" : user.riskScore > 30 ? "text-accent-warning" : "text-accent-safe"}>
                    <AnimatedNumber value={user.riskScore} />
                  </span>
                  <span className="text-2xl text-muted-foreground/50">/100</span>
                </div>
                <Badge variant={user.riskScore > 75 ? "danger" : user.riskScore > 30 ? "warning" : "success"} className="text-sm px-4 py-1">
                  {user.status}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants} className="lg:col-span-2">
          <Card className="h-full">
           <CardHeader>
            <CardTitle>Recent Alert Flags</CardTitle>
            <CardDescription>Anomalies detected in the ongoing session.</CardDescription>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <div className="flex h-32 items-center justify-center border border-dashed border-white/10 rounded-lg bg-white/5">
                 <p className="text-muted-foreground text-sm">No recent alerts found for this user.</p>
              </div>
            ) : (
              <ul className="space-y-3">
                {alerts.map(alert => (
                  <li key={alert.id} className="flex items-start gap-4 p-4 border rounded-lg bg-destructive/10 border-destructive/20 shadow-sm">
                    <ShieldAlert className="h-5 w-5 text-accent-danger mt-0.5 drop-shadow-glow-danger" />
                    <div>
                      <p className="font-medium text-destructive">{alert.type}</p>
                      <p className="text-xs text-muted-foreground mt-1">{getRelativeTime(alert.timestamp)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        </motion.div>
      </div>

      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle>Activity Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative border-l border-white/10 ml-4 space-y-8 py-4">
              {timeline.map((event) => (
                <div key={event.id} className="relative pl-8">
                  <span className="absolute -left-3 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/50 border-2 border-primary shadow-glow">
                    <Clock className="h-3 w-3 text-primary" />
                  </span>
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-white">{event.action}</span>
                    <span className="text-xs text-muted-foreground mt-0.5">{getRelativeTime(event.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
