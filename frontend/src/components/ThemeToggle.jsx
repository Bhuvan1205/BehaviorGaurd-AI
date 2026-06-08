import { Moon, Sun } from "lucide-react";
import { useTheme } from "../theme/theme";

export function ThemeToggle() {
  const { isDark, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-slate-950/80 text-slate-100 shadow-lg shadow-black/20 transition hover:border-cyan-400/30"
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
