import { useState } from "react";
import { Shield } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ThemeToggle } from "../components/ThemeToggle";
import { useAuthStore } from "../store/useAuthStore";

export function SignInPage() {
  const navigate = useNavigate();
  const signIn = useAuthStore((state) => state.signIn);
  const register = useAuthStore((state) => state.register);
  const isLoading = useAuthStore((state) => state.isLoading);
  const authError = useAuthStore((state) => state.error);
  const [mode, setMode] = useState("signin");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [registerForm, setRegisterForm] = useState({
    employee_id: "",
    full_name: "",
    username: "",
    password: "",
  });

  const updateLogin = (field) => (event) => {
    setLoginForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const updateRegister = (field) => (event) => {
    setRegisterForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleSignIn = async (event) => {
    event.preventDefault();
    try {
      await signIn(loginForm);
      navigate("/", { replace: true });
    } catch {
      // store already updated
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    try {
      await register(registerForm);
      toast.success("Admin account created.", {
        description: "You can now sign in with the new credentials.",
      });
      setMode("signin");
      setLoginForm({ username: registerForm.username, password: registerForm.password });
    } catch {
      // store already updated
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-app px-6 py-12 text-slate-100">
      <div className="absolute right-6 top-6 z-20">
        <ThemeToggle />
      </div>
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        className="absolute inset-0 h-full w-full object-cover opacity-[0.12] blur-[1px] saturate-50"
      >
        <source src="/bg-theme.mp4.mp4" type="video/mp4" />
      </video>
      <div className="absolute inset-0 bg-slate-950/88" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,211,238,0.06),transparent_24%),radial-gradient(circle_at_80%_20%,rgba(56,189,248,0.04),transparent_20%)]" />
      <div className="relative mx-auto flex min-h-[calc(100vh-6rem)] max-w-6xl items-center">
        <div className="grid w-full gap-8 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="rounded-[2.5rem] border border-white/10 bg-slate-950/60 p-10 shadow-2xl shadow-black/25 backdrop-blur">
            <div className="inline-flex items-center gap-3 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm font-medium text-cyan-200">
              <Shield size={16} />
              BehaviorGuard-AI
            </div>
            <h1 className="mt-8 max-w-xl text-5xl font-semibold tracking-tight text-white">
              Security analytics with live behavioral context.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-slate-400">
              Sign in to access organization-wide monitoring, alert triage, user-level investigation, and simulation workflows backed directly by PostgreSQL.
            </p>

          </section>

          <section className="rounded-[2.5rem] border border-white/10 bg-slate-950/80 p-8 shadow-2xl shadow-black/30 backdrop-blur sm:p-10">
            <div className="flex gap-2 rounded-full border border-white/10 bg-white/[0.03] p-1">
              {[
                ["signin", "Sign in"],
                ["register", "Register"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setMode(value)}
                  className={[
                    "flex-1 rounded-full px-4 py-2 text-sm font-medium transition",
                    mode === value ? "bg-cyan-400/12 text-white" : "text-slate-400 hover:text-slate-200",
                  ].join(" ")}
                >
                  {label}
                </button>
              ))}
            </div>

            {mode === "signin" ? (
              <form className="mt-10 space-y-5" onSubmit={handleSignIn}>
                <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">Sign In</p>
                <h2 className="text-3xl font-semibold text-white">Analyst access</h2>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-300">Username</span>
                  <input value={loginForm.username} onChange={updateLogin("username")} className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-white outline-none transition focus:border-cyan-400/40" required />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-300">Password</span>
                  <input type="password" value={loginForm.password} onChange={updateLogin("password")} className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-white outline-none transition focus:border-cyan-400/40" required />
                </label>
                <button type="submit" disabled={isLoading} className="inline-flex w-full items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:opacity-60">
                  {isLoading ? "Signing in..." : "Enter console"}
                </button>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">
                  Demo credentials:
                  <span className="ml-2 font-medium text-white">analyst</span>
                  <span className="mx-2 text-slate-500">/</span>
                  <span className="font-medium text-white">Admin@123</span>
                </div>
              </form>
            ) : (
              <form className="mt-10 space-y-5" onSubmit={handleRegister}>
                <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">Register</p>
                <h2 className="text-3xl font-semibold text-white">Create admin access</h2>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-300">Employee ID</span>
                  <input value={registerForm.employee_id} onChange={updateRegister("employee_id")} className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-white outline-none transition focus:border-cyan-400/40" required />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-300">Full name</span>
                  <input value={registerForm.full_name} onChange={updateRegister("full_name")} className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-white outline-none transition focus:border-cyan-400/40" required />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-300">Username</span>
                  <input value={registerForm.username} onChange={updateRegister("username")} className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-white outline-none transition focus:border-cyan-400/40" required />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-300">Password</span>
                  <input type="password" value={registerForm.password} onChange={updateRegister("password")} className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-white outline-none transition focus:border-cyan-400/40" required />
                </label>
                <button type="submit" disabled={isLoading} className="inline-flex w-full items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:opacity-60">
                  {isLoading ? "Creating account..." : "Create admin"}
                </button>
              </form>
            )}

            {authError ? (
              <div className="mt-5 rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
                {authError}
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
}
