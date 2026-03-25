import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, FileText, AlertTriangle, LogOut, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const links = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Risk Analyzer', path: '/analyzer', icon: Activity },
  { name: 'Monitoring', path: '/monitoring', icon: Users },
  { name: 'Alerts', path: '/alerts', icon: AlertTriangle },
  { name: 'Reports', path: '/reports', icon: FileText },
];

export function Sidebar({ className }) {
  return (
    <aside className={cn("pb-12 min-h-screen w-64 border-r border-white/5 bg-black/40 backdrop-blur-md pt-20 flex flex-col fixed left-0 top-0 z-30", className)}>
      <div className="space-y-6 py-6 flex-1">
        <div className="px-4">
          <h2 className="mb-4 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground/50">
            Overview
          </h2>
          <nav className="space-y-1.5">
            {links.map((link) => (
              <NavLink
                key={link.name}
                to={link.path}
                className={({ isActive }) =>
                  cn(
                    "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 overflow-hidden",
                    isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.div
                        layoutId="activeTab"
                        className="absolute inset-0 bg-primary/10 border border-primary/20 rounded-lg"
                        initial={false}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                      />
                    )}
                    <link.icon className={cn("h-4 w-4 relative z-10 transition-colors", isActive ? "text-primary" : "group-hover:text-foreground")} />
                    <span className="relative z-10">{link.name}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
      <div className="p-4 mt-auto border-t border-white/5">
        <NavLink to="/login" className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all duration-200">
          <LogOut className="h-4 w-4" />
          Sign Out
        </NavLink>
      </div>
    </aside>
  );
}
