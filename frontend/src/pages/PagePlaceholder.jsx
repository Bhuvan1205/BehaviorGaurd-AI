export function PagePlaceholder({ icon: Icon, eyebrow, title, description }) {
  return (
    <section className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-8 shadow-2xl shadow-black/20 backdrop-blur sm:p-10">
      <div className="mb-6 inline-flex rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 text-cyan-300">
        <Icon size={28} />
      </div>
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-400">
        {eyebrow}
      </p>
      <h1 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">{title}</h1>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
        {description}
      </p>
    </section>
  );
}
