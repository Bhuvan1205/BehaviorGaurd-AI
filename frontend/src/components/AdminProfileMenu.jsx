import { useEffect, useRef, useState } from "react";
import { LogOut, UserCircle2 } from "lucide-react";
import { useAuthStore } from "../store/useAuthStore";

export function AdminProfileMenu() {
  const admin = useAuthStore((state) => state.admin);
  const signOut = useAuthStore((state) => state.signOut);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  if (!admin) {
    return null;
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-label="Open admin profile"
        onClick={() => setIsOpen((value) => !value)}
        className="profile-trigger inline-flex h-11 w-11 items-center justify-center rounded-full border shadow-lg shadow-black/20 transition"
      >
        <UserCircle2 size={20} />
      </button>

      {isOpen ? (
        <div className="absolute right-0 top-[calc(100%+0.85rem)] z-40 w-72 rounded-[1.8rem] border border-white/10 bg-slate-950/95 p-4 text-sm text-slate-300 shadow-[0_20px_60px_rgba(2,6,23,0.45)] backdrop-blur-xl">
          <div className="flex items-start gap-3">
            <span className="profile-badge rounded-2xl border p-2.5">
              <UserCircle2 size={18} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-base font-semibold text-white">{admin.full_name}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.22em] text-slate-500">
                {admin.employee_id}
              </p>
              <p className="mt-2 text-sm text-slate-400">{admin.username}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={signOut}
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-[1.2rem] border border-white/10 bg-slate-900/90 px-3 py-3 text-sm font-medium text-slate-100 transition hover:bg-slate-800"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}
