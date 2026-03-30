function Section({ eyebrow, title, children }) {
  return (
    <section className="rounded-[1.9rem] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20 sm:p-8">
      <p className="text-[11px] font-semibold uppercase tracking-[0.34em] text-cyan-400">
        {eyebrow}
      </p>
      <h2 className="mt-3 text-2xl font-semibold text-white sm:text-3xl">{title}</h2>
      <div className="mt-4 space-y-4 text-sm leading-7 text-slate-400 sm:text-base">
        {children}
      </div>
    </section>
  );
}

export function AboutPage() {
  return (
    <div className="space-y-6">
      <section className="rounded-[2.2rem] border border-white/10 bg-slate-950/72 px-8 py-10 shadow-2xl shadow-black/20">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.03em] text-white sm:text-5xl">
            Behavioral risk analysis for modern enterprise monitoring
          </h1>
          <p className="mt-5 text-sm leading-7 text-slate-400 sm:text-base">
            BehaviorGuard AI is a UEBA-style platform built to detect unusual user activity inside
            an organization. It combines database-backed monitoring, contextual feature engineering,
            and machine learning to help analysts understand when a user&apos;s behavior starts to move
            outside their normal operating pattern.
          </p>
        </div>
      </section>

      <Section eyebrow="Workflow" title="How The System Works">
        <p>
          The platform uses PostgreSQL as the source of truth for users, roles, departments, login
          history, risk windows, and alerts. The main dashboard presents organization-wide analytics,
          while the user analytics view focuses on a selected investigation target and shows that
          user&apos;s individual behavior, risk trend, and alert context.
        </p>
        <p>
          When a new event is processed, the backend looks at the current event together with recent
          historical behavior for that user. It then generates a structured feature set, runs the ML
          inference pipeline, converts the result into a calibrated risk score, and stores the output
          back in the database for monitoring and investigation.
        </p>
      </Section>

      <Section eyebrow="Model" title="Machine Learning Approach">
        <p>
          The project uses an Isolation Forest model for anomaly detection. This model is useful for
          insider-risk analysis because it does not require large volumes of perfectly labeled attack
          data. Instead, it learns which behavior patterns look isolated or unusual in feature
          space, making it suitable for spotting deviations from expected user activity.
        </p>
        <p>
          The production inference path also uses a saved feature order and scaler so the live
          backend stays aligned with the model&apos;s training pipeline. That keeps inference stable and
          avoids mismatches between the model and the features it receives at runtime.
        </p>
      </Section>

      <Section eyebrow="Features" title="Why Two Inputs Can Produce Rich Analysis">
        <p>
          The simulator keeps the interface simple by asking for only two direct inputs: logons and
          devices. However, those are only the visible inputs. The backend expands them into a
          larger behavioral feature vector using the selected user&apos;s recent history, event timing,
          activity rhythm, device usage pattern, and deviation from baseline.
        </p>
        <p>
          In practice, this means the model is not judging two numbers in isolation. It is judging
          how those values relate to the user&apos;s own recent pattern. The same input can therefore
          produce different outcomes for different users because the surrounding behavioral context
          is different.
        </p>
      </Section>

      <Section eyebrow="Output" title="How Risk And Alerts Are Interpreted">
        <p>
          The model produces an anomaly-oriented score, and the backend converts that into an easier
          to understand risk percentage. That risk is then categorized into readable levels such as
          low, guarded, elevated, or high. Stronger events may contribute to alert generation,
          while lower-severity signals are still preserved as part of the user&apos;s behavioral record.
        </p>
        <p>
          This design allows the platform to stay useful at both levels: it can provide a broad
          organization-wide view of current posture, while also supporting a deeper per-user
          investigation workflow when analysts need to drill into a specific case.
        </p>
      </Section>
    </div>
  );
}
