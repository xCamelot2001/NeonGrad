import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-6 bg-gradient-to-br from-slate-950 via-slate-900 to-brand-900">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 flex items-center justify-between px-8 py-4 border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm z-10">
        <span className="text-xl font-bold text-brand-500">NeonGrad</span>
        <Link
          href="/auth"
          className="px-4 py-2 text-sm font-medium rounded-lg bg-brand-500 hover:bg-brand-600 transition-colors"
        >
          Get started
        </Link>
      </nav>

      {/* Hero */}
      <section className="text-center max-w-3xl mt-24 mb-16">
        <div className="inline-block px-3 py-1 mb-6 text-xs font-semibold tracking-wider uppercase text-brand-500 bg-brand-500/10 rounded-full border border-brand-500/20">
          AI-Powered Job Hunting
        </div>
        <h1 className="text-5xl font-bold leading-tight mb-6">
          NeonGrad finds the jobs.{" "}
          <span className="text-brand-500">You land them.</span>
        </h1>
        <p className="text-xl text-slate-400 mb-10 leading-relaxed">
          Set your preferences once. Every morning, NeonGrad surfaces your best
          opportunities — ranked by AI-assessed fit, with gap analysis and tailored
          applications ready in 60 seconds.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/auth"
            className="px-8 py-3 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 transition-colors"
          >
            Start for free
          </Link>
          <a
            href="https://github.com"
            className="px-8 py-3 font-semibold rounded-xl border border-slate-700 hover:border-slate-500 transition-colors"
          >
            View on GitHub
          </a>
        </div>
      </section>

      {/* Feature cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full mb-20">
        {[
          {
            icon: "🎯",
            title: "Daily Job Discovery",
            desc: "Automatically finds new relevant jobs across Adzuna every morning based on your preferences.",
          },
          {
            icon: "🤖",
            title: "AI Fit Scoring",
            desc: "Fine-tuned ML model + Claude gap analysis tells you exactly where you match and what you're missing.",
          },
          {
            icon: "⚡",
            title: "60-Second Applications",
            desc: "One click tailors your CV and cover letter to a specific job — with a judge loop for quality.",
          },
        ].map((f) => (
          <div
            key={f.title}
            className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 hover:border-brand-500/30 transition-colors"
          >
            <div className="text-3xl mb-3">{f.icon}</div>
            <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
            <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </section>

      <footer className="text-slate-600 text-sm pb-8">
        Built by Hossein · Next.js · FastAPI · LangGraph · Claude API · Supabase
      </footer>
    </main>
  );
}
