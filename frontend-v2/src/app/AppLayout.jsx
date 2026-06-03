import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { PageLayout } from "../components/PageLayout";
import { Sidebar } from "../components/Sidebar";
import { useAppStore } from "../store/useAppStore";
import { useLiveStore } from "../store/useLiveStore";

export function AppLayout() {
  const startAutoRefresh = useAppStore((state) => state.startAutoRefresh);
  const stopAutoRefresh  = useAppStore((state) => state.stopAutoRefresh);
  const openStream       = useLiveStore((state) => state.openStream);
  const closeStream      = useLiveStore((state) => state.closeStream);

  useEffect(() => {
    startAutoRefresh(15000);
    openStream();          // open SSE once — persists across all page navigation
    return () => {
      stopAutoRefresh();
      closeStream();       // only closes on logout / app unmount
    };
  }, [startAutoRefresh, stopAutoRefresh, openStream, closeStream]);

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
