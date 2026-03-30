export function ProjectLogo({ expanded = false }) {
  return (
    <div className={`flex items-center ${expanded ? "gap-3" : "justify-center"}`}>
      <div className="brand-mark flex h-11 w-11 items-center justify-center rounded-[1.1rem] border shadow-[inset_0_0_0_1px_rgba(255,255,255,0.04)]">
        <svg
          viewBox="0 0 48 48"
          className="brand-mark-icon h-6 w-6"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M24 6L36 11V20C36 28.2 31.2 35.65 24 39C16.8 35.65 12 28.2 12 20V11L24 6Z"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinejoin="round"
          />
          <path
            d="M16.5 24C18.4 20.9 20.95 19.35 24 19.35C27.05 19.35 29.6 20.9 31.5 24C29.6 27.1 27.05 28.65 24 28.65C20.95 28.65 18.4 27.1 16.5 24Z"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinejoin="round"
          />
          <circle cx="24" cy="24" r="2.7" fill="currentColor" />
        </svg>
      </div>

      {expanded ? (
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.34em] text-slate-500">
            BehaviorGuard
          </p>
          <p className="mt-1 text-sm font-semibold text-white">Security Analytics</p>
        </div>
      ) : null}
    </div>
  );
}
