import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { PageLayout } from "../components/PageLayout";
import { Sidebar } from "../components/Sidebar";
import { useAppStore } from "../store/useAppStore";

export function AppLayout() {
  const loadUsers = useAppStore((state) => state.loadUsers);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-app text-slate-100">
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        className="absolute inset-0 h-full w-full object-cover opacity-[0.14] blur-[1px] saturate-50"
      >
        <source src="/bg-theme.mp4.mp4" type="video/mp4" />
      </video>
      <div className="absolute inset-0 bg-slate-950/86" />
      <div className="relative z-10 min-h-screen">
        <Sidebar />
        <PageLayout>
          <Outlet />
        </PageLayout>
      </div>
    </div>
  );
}
