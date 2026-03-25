import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, FileText, PieChart as PieChartIcon, Target } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';

const RISK_TIERS = [
  { name: 'Safe Users', value: 400, color: '#10b981' },
  { name: 'Moderate Risk', value: 300, color: '#f59e0b' },
  { name: 'High Risk', value: 50, color: '#ef4444' },
];

export default function Reports() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Reports</h1>
          <p className="text-muted-foreground mt-2">Generate and export behavior analytics reports.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" /> Export CSV
          </Button>
          <Button className="gap-2">
            <FileText className="h-4 w-4" /> Export PDF
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Risk Distribution Breakdown
            </CardTitle>
            <CardDescription>Current snapshot of user risk categorization.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={RISK_TIERS}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {RISK_TIERS.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ backgroundColor: '#111', border: 'none', borderRadius: '8px', color: '#fff' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
             <CardTitle className="flex items-center gap-2">
              <PieChartIcon className="h-5 w-5 text-primary" />
              Weekly Anomaly Summary
            </CardTitle>
            <CardDescription>Types of anomalies detected over the last 7 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6 mt-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Failed Logins</span>
                  <span className="text-muted-foreground">45%</span>
                </div>
                <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-accent-warning" style={{ width: '45%' }}></div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Multiple IPs</span>
                  <span className="text-muted-foreground">30%</span>
                </div>
                <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                   <div className="h-full bg-accent-danger" style={{ width: '30%' }}></div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Unusual Downloads</span>
                  <span className="text-muted-foreground">25%</span>
                </div>
                <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                   <div className="h-full bg-primary" style={{ width: '25%' }}></div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
