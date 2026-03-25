import React, { memo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useRealTime } from '@/context/RealTimeContext';
import { getRelativeTime } from '@/utils/time';

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  show: { opacity: 1, x: 0, transition: { type: "tween", ease: "easeOut", duration: 0.3 } }
};

const getStatusBadge = (status) => {
  if (status === 'Safe') return <Badge variant="success" className="bg-accent-safe/10 text-accent-safe hover:bg-accent-safe/20 border border-accent-safe/20 shadow-glow">{status}</Badge>;
  if (status === 'Moderate') return <Badge variant="warning" className="bg-accent-warning/10 text-accent-warning hover:bg-accent-warning/20 border border-accent-warning/20 shadow-glow">{status}</Badge>;
  return <Badge variant="danger" className="bg-accent-danger/10 text-accent-danger hover:bg-accent-danger/20 border border-accent-danger/20 shadow-glow-danger">{status}</Badge>;
};

const UserRow = memo(({ user, onClick }) => {
  return (
    <TableRow 
      className="cursor-pointer border-white/5 hover:bg-white/5 transition-colors"
      onClick={() => onClick(user.id)}
    >
      <TableCell className="font-medium text-white">{user.username}</TableCell>
      <TableCell className="text-muted-foreground">{getRelativeTime(user.lastActivity || Date.now())}</TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <span className={`transition-colors duration-500 ${user.riskScore > 75 ? "text-accent-danger font-bold text-shadow-danger" : user.riskScore > 30 ? "text-accent-warning" : "text-accent-safe"}`}>
            {user.riskScore}
          </span>
        </div>
      </TableCell>
      <TableCell>{getStatusBadge(user.status)}</TableCell>
    </TableRow>
  );
});

export default function Monitoring() {
  const { users } = useRealTime();
  const navigate = useNavigate();

  const handleRowClick = useCallback((id) => {
    navigate(`/user/${id}`);
  }, [navigate]);

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariants} className="flex items-center gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white drop-shadow-sm">User Monitoring</h1>
          <p className="text-muted-foreground mt-2">Live tracking of user behavior patterns and risk updates.</p>
        </div>
        <span className="relative flex h-2.5 w-2.5 ml-auto">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary"></span>
        </span>
      </motion.div>

      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle>Active Users</CardTitle>
            <CardDescription>A real-time list of users and their shifting risk scores.</CardDescription>
          </CardHeader>
          <CardContent>
            {users.length === 0 ? (
              <div className="animate-pulse space-y-4">
                <div className="h-10 bg-white/5 rounded"></div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-white/5 hover:bg-transparent">
                    <TableHead>Username</TableHead>
                    <TableHead>Last Activity</TableHead>
                    <TableHead>Risk Score</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <UserRow key={user.id} user={user} onClick={handleRowClick} />
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
