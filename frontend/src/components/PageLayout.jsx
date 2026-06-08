import { AdminProfileMenu } from "./AdminProfileMenu";
import { ThemeToggle } from "./ThemeToggle";

export function PageLayout({ children }) {
  return (
    <div className="flex min-h-screen flex-1 flex-col xl:pl-[7.5rem]">
      <header className="z-20 px-4 pt-4 sm:px-6 lg:px-8">
        <div className="relative mx-auto flex h-20 w-full max-w-[92rem] items-center justify-center rounded-[1.6rem] border border-white/10 bg-slate-950/72 px-5 shadow-xl shadow-black/20 backdrop-blur-xl">
          <div className="text-center">
            <h2 className="text-[1.2rem] font-semibold uppercase tracking-[0.28em] text-white">
              BehaviorGuard AI
            </h2>
          </div>
          <div className="absolute right-5 top-1/2 flex -translate-y-1/2 items-center gap-3">
            <ThemeToggle />
            <AdminProfileMenu />
          </div>
        </div>
      </header>

      <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[92rem]">{children}</div>
      </main>
    </div>
  );
}
