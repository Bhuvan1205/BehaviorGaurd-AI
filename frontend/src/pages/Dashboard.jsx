import React, { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, Activity, AlertTriangle, ShieldAlert, Activity as ActivityIcon } from 'lucide-react';
import { useRealTime } from '@/context/RealTimeContext';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import { AnimatedNumber } from '@/components/ui/animated-number';
import { getRelativeTime } from '@/utils/time';

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function Dashboard() {
  const { dashboardMetrics: metrics, activityFeed } = useRealTime();

  const riskTrendChart = useMemo(() => (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={metrics.riskHistory} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis dataKey="time" stroke="#666" fontSize={12} tickLine={false} axisLine={false} dy={10} />
        <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} dx={-10} domain={[0, 100]} />
        <RechartsTooltip 
          contentStyle={{ backgroundColor: 'rgba(10,10,12,0.8)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} 
          itemStyle={{ color: '#ef4444' }}
          animationDuration={200}
        />
        <Area isAnimationActive={true} animationDuration={800} animationEasing="ease-out" type="monotone" dataKey="score" stroke="#ef4444" strokeWidth={3} fillOpacity={1} fill="url(#colorScore)" activeDot={{ r: 6, fill: '#ef4444', strokeWidth: 0, shadow: '0 0 10px rgba(239,68,68,0.5)' }} />
      </AreaChart>
    </ResponsiveContainer>
  ), [metrics?.riskHistory]);

  const activityBarChart = useMemo(() => (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={metrics.activityDistribution} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis dataKey="name" stroke="#666" fontSize={12} tickLine={false} axisLine={false} dy={10} />
        <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
        <RechartsTooltip 
          cursor={{fill: 'rgba(255,255,255,0.02)'}}
          contentStyle={{ backgroundColor: 'rgba(10,10,12,0.8)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} 
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={true} animationDuration={800}>
          {metrics.activityDistribution.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#10b981' : '#047857'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  ), [metrics?.activityDistribution]);

  if (!metrics) return null;

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white drop-shadow-sm">System Overview</h1>
        <p className="text-muted-foreground mt-1 text-sm flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary"></span>
          </span>
          Live monitoring active
        </p>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Metric Cards remain same */}
        <motion.div variants={itemVariants}>
          <Card className="relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Users</CardTitle>
              <Users className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tighter text-white">
                <AnimatedNumber value={metrics.totalUsers} />
              </div>
            </CardContent>
          </Card>
        </motion.div>
        {/* Same for others */}
        <motion.div variants={itemVariants}>
          <Card className="relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Active Sessions</CardTitle>
              <Activity className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tighter text-white">
                <AnimatedNumber value={metrics.activeSessions} />
              </div>
            </CardContent>
          </Card>
        </motion.div>
        <motion.div variants={itemVariants}>
          <Card className="relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-destructive/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Risk Alerts</CardTitle>
              <AlertTriangle className="h-4 w-4 text-destructive drop-shadow-glow-danger" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tighter text-white">
                <AnimatedNumber value={metrics.riskAlerts} />
              </div>
            </CardContent>
          </Card>
        </motion.div>
        <motion.div variants={itemVariants}>
          <Card className="relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Avg Risk Score</CardTitle>
              <ShieldAlert className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tighter text-white">
                <AnimatedNumber value={metrics.averageRiskScore} percent={true} />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
        <motion.div variants={itemVariants} className="col-span-4 h-full">
          <Card className="h-full flex flex-col">
            <CardHeader>
              <CardTitle className="text-foreground/90 font-semibold">Live Risk Engine Trend</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px] pl-0">
              {riskTrendChart}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants} className="col-span-3 h-[400px]">
          <Card className="h-full flex flex-col overflow-hidden">
            <CardHeader className="border-b border-white/5 pb-4 bg-background/50">
              <CardTitle className="text-foreground/90 font-semibold flex items-center justify-between">
                <span>Live Activity Feed</span>
                <ActivityIcon className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden relative">
              <div className="absolute inset-0 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                <AnimatePresence initial={false}>
                  {activityFeed.map((activity) => (
                    <motion.div
                      layout
                      key={activity.id}
                      initial={{ opacity: 0, scale: 0.9, y: -20 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                      className="p-3 rounded-lg border border-white/5 bg-black/40 flex flex-col gap-1 shadow-sm"
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-semibold uppercase tracking-wider ${activity.type === 'anomaly' ? 'text-accent-danger' : 'text-primary'}`}>
                          {activity.type}
                        </span>
                        <span className="text-xs text-muted-foreground">{getRelativeTime(activity.timestamp)}</span>
                      </div>
                      <p className="text-sm text-foreground/80">{activity.message}</p>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </motion.div>
  );
}
