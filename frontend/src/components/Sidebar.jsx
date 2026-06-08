import {
  ArrowUpRight,
  AlertTriangle,
  LayoutDashboard,
  CloudUpload,
  ShieldUser,
  ShieldAlert,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAppStore } from "../store/useAppStore";
import { ProjectLogo } from "./ProjectLogo";
import { UserSelect } from "./UserSelect";

export function Sidebar() {
  const selectedUserId = useAppStore((state) => state.selectedUserId);

  const navigation = [
    {
      label: "Dashboard",
      to: "/",
      icon: LayoutDashboard,
      end: true,
      tone: "nav-dashboard",
      iconTone: "nav-icon-dashboard",
    },
    {
      label: "Data Upload",
      to: "/upload",
      icon: CloudUpload,
      tone: "nav-monitoring",
      iconTone: "nav-icon-monitoring",
    },
    {
      label: "Alerts",
      to: "/alerts",
      icon: AlertTriangle,
      tone: "nav-alerts",
      iconTone: "nav-icon-alerts",
    },
    {
      label: "Email Security",
      to: "/email-security",
      icon: ShieldAlert,
      tone: "nav-monitoring",
      iconTone: "nav-icon-monitoring",
    },
    {
      label: "User Analytics",
      to: selectedUserId ? `/user/${selectedUserId}` : "/user-analytics",
      icon: ShieldUser,
      tone: "nav-analytics",
      iconTone: "nav-icon-analytics",
    },
  ];

  return (
    <aside className="pointer-events-none fixed inset-y-0 left-0 z-30 hidden xl:block">
      <div
        className="group/sidebar pointer-events-auto m-5 flex h-[calc(100vh-2.5rem)] w-[5.7rem] flex-col rounded-[2.2rem] border border-white/10 bg-slate-950/72 p-4 shadow-[0_20px_70px_rgba(2,6,23,0.45)] backdrop-blur-xl transition-all duration-300 hover:w-[17.2rem]"
      >
        <div className="px-1">
          <div className="group-hover/sidebar:hidden">
            <ProjectLogo expanded={false} />
          </div>
          <div className="hidden group-hover/sidebar:block">
            <ProjectLogo expanded />
          </div>
        </div>

        <nav className="mt-8 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.end}
                title={item.label}
                className={({ isActive }) =>
                  [
                    `group nav-item ${item.tone} flex items-center rounded-[1.35rem] px-3 py-3 text-sm font-medium transition-all duration-200`,
                    "justify-center group-hover/sidebar:justify-start group-hover/sidebar:gap-3",
                    isActive
                      ? "nav-item-active text-white"
                      : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-100",
                  ].join(" ")
                }
              >
                <span
                  className={`nav-item-icon ${item.iconTone} rounded-[1rem] border border-white/10 bg-slate-900/80 p-2.5`}
                >
                  <Icon size={18} />
                </span>
                <span className="hidden group-hover/sidebar:block">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-4 hidden group-hover/sidebar:block">
          <UserSelect />
        </div>

        <div className="mt-auto group-hover/sidebar:hidden" />

        <NavLink
          to="/about"
          className="mt-auto hidden rounded-[1.8rem] border border-white/10 bg-white/[0.035] p-4 transition hover:bg-white/[0.055] group-hover/sidebar:mt-2.5 group-hover/sidebar:block"
        >
          <div className="flex items-center justify-between gap-3 rounded-[1.35rem]">
            <span className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-500">
              About
            </span>
            <span className="text-slate-500 transition group-hover/sidebar:text-slate-300">
              <ArrowUpRight size={16} />
            </span>
          </div>
        </NavLink>
      </div>
    </aside>
  );
}
