import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ShieldAlert, Filter, Search } from 'lucide-react';
import { useRealTime } from '@/context/RealTimeContext';
import { motion, AnimatePresence } from 'framer-motion';
import { getRelativeTime } from '@/utils/time';

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};
const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function Alerts() {
  const { alerts } = useRealTime();

  const getSeverityBadge = (severity) => {
    if (severity === 'High') return <Badge variant="danger" className="bg-accent-danger/10 text-accent-danger border border-accent-danger/20">{severity}</Badge>;
    if (severity === 'Medium') return <Badge variant="warning" className="bg-accent-warning/10 text-accent-warning border border-accent-warning/20">{severity}</Badge>;
    return <Badge variant="secondary" className="bg-white/5 text-muted-foreground border border-white/10">{severity}</Badge>;
  };

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white drop-shadow-sm">System Alerts</h1>
          <p className="text-muted-foreground mt-2">Live stream of detected anomalies and policy violations.</p>
        </div>
        <div className="flex items-center gap-2">
           <Button variant="outline" className="gap-2 border-white/10">
            <Filter className="h-4 w-4" /> Filter
          </Button>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="search"
              placeholder="Search alerts..."
              className="h-10 w-[200px] lg:w-[300px] rounded-md border border-white/10 bg-black/40 pl-8 pr-3 text-sm text-white placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring transition-colors"
            />
          </div>
        </div>
      </motion.div>

      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground/90">
              <ShieldAlert className="h-5 w-5 text-accent-danger" /> 
              Active Anomalies Stream
            </CardTitle>
            <CardDescription>Real-time queue of security events requiring attention.</CardDescription>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <div className="text-muted-foreground text-center py-8">No alerts active.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-white/5 hover:bg-transparent">
                    <TableHead>Event Type</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Time</TableHead>
                    <TableHead>User ID</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <AnimatePresence initial={false}>
                    {alerts.map((alert) => (
                      <motion.tr 
                        key={alert.id}
                        initial={{ opacity: 0, x: -10, backgroundColor: 'rgba(239, 68, 68, 0.1)' }}
                        animate={{ opacity: 1, x: 0, backgroundColor: 'transparent' }}
                        transition={{ duration: 0.5 }}
                        className="border-white/5 hover:bg-white/5 transition-colors"
                      >
                        <TableCell className="font-medium text-white">{alert.type}</TableCell>
                        <TableCell>{getSeverityBadge(alert.severity)}</TableCell>
                        <TableCell className="text-muted-foreground">{getRelativeTime(alert.timestamp)}</TableCell>
                        <TableCell className="text-muted-foreground">User #{alert.userId}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" className="hover:bg-primary/10 hover:text-primary transition-colors">Investigate</Button>
                        </TableCell>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
