import Link from "next/link";

// ── Mock UI preview data ──────────────────────────────────────────────────────

const MOCK_JOBS = [
  { title: "ML Engineer", company: "Anthropic", score: 94, strategy: "strong_match", matched: ["PyTorch", "LangChain"], missing: [] },
  { title: "AI Research Engineer", company: "DeepMind", score: 81, strategy: "decent", matched: ["Python", "Transformers"], missing: ["JAX"] },
  { title: "Backend Engineer", company: "Stripe", score: 67, strategy: "stretch", matched: ["FastAPI"], missing: ["Go", "Kafka"] },
];

const STRATEGY_STYLE: Record<string, { pill: string; ring: string; score: string }> = {
  strong_match: { pill: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", ring: "#10b981", score: "text-emerald-400" },
  decent:       { pill: "bg-blue-500/15 text-blue-400 border-blue-500/30",         ring: "#3b82f6", score: "text-blue-400"   },
  stretch:      { pill: "bg-amber-500/15 text-amber-400 border-amber-500/30",      ring: "#f59e0b", score: "text-amber-400"  },
};
const STRATEGY_LABEL: Record<string, string> = {
  strong_match: "Strong match",
  decent: "Decent",
  stretch: "Stretch",
};

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Upload your CV & set preferences",
    desc: "Paste or upload your CV. Tell NeonGrad your target roles, locations, and salary range — once, and you're done.",
    icon: "📄",
  },
  {
    step: "02",
    title: "Wake up to ranked jobs",
    desc: "Every morning, the discovery agent pulls fresh listings and the ranking agent scores them against your profile — fit score, gap analysis, strategy.",
    icon: "🎯",
  },
  {
    step: "03",
    title: "One click to a tailored application",
    desc: "Hit Tailor & Apply. A LangGraph agent researches the company, rewrites your CV bullets, writes a personalised cover letter, and a judge loop scores the output before saving.",
    icon: "⚡",
  },
];

const TECH_STACK = [
  "Next.js 15", "FastAPI", "LangGraph", "Groq / Llama 3.1",
  "Supabase", "sentence-transformers", "Tavily", "Adzuna API",
];

// ── Components ────────────────────────────────────────────────────────────────

function MockScoreRing({ score, strategy }: { score: number; strategy: string }) {
  const cfg = STRATEGY_STYLE[strategy];
  const deg = (score / 100) * 360;
  return (
    <div className="shrink-0 flex flex-col items-center gap-1">
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center"
        style={{ background: `conic-gradient(${cfg.ring} ${deg}deg, #1e293b 0deg)` }}
      >
        <div className="w-8 h-8 rounded-full bg-slate-900 flex items-center justify-center">
          <span className={`text-xs font-bold ${cfg.score}`}>{score}%</span>
        </div>
      </div>
      <span className="text-[10px] text-slate-600">fit</span>
    </div>
  );
}

function MockDashboard() {
  return (
    <div className="rounded-2xl border border-slate-700/60 bg-slate-900/80 backdrop-blur overflow-hidden shadow-2xl shadow-black/50 w-full max-w-lg">
      {/* Mock browser bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-800/60 border-b border-slate-700/60">
        <span className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
        <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
        <span className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
        <span className="ml-3 text-xs text-slate-500 font-mono">neongrad.app/dashboard</span>
      </div>

      {/* Mock nav */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
        <span className="text-sm font-bold text-brand-500">NeonGrad</span>
        <div className="flex gap-4 text-xs text-slate-500">
          <span className="text-slate-100">Dashboard</span>
          <span>Applications</span>
          <span>Profile</span>
        </div>
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-3 gap-2 px-4 pt-4 pb-2">
        {[
          { label: "Strong match", count: 3, color: "text-emerald-400", bg: "bg-emerald-500/10" },
          { label: "Decent fit",   count: 7, color: "text-blue-400",    bg: "bg-blue-500/10"   },
          { label: "Stretch",      count: 4, color: "text-amber-400",   bg: "bg-amber-500/10"  },
        ].map(({ label, count, color, bg }) => (
          <div key={label} className={`rounded-xl border border-slate-800 p-3 ${bg}`}>
            <p className={`text-xl font-bold ${color}`}>{count}</p>
            <p className="text-[10px] text-slate-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Job cards */}
      <div className="px-4 pb-4 space-y-2 mt-2">
        {MOCK_JOBS.map((job) => {
          const cfg = STRATEGY_STYLE[job.strategy];
          return (
            <div
              key={job.title}
              className="flex items-start gap-3 p-3 rounded-xl border border-slate-800 bg-slate-900/60"
            >
              <MockScoreRing score={job.score} strategy={job.strategy} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-slate-100">{job.title}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border ${cfg.pill}`}>
                    {STRATEGY_LABEL[job.strategy]}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{job.company}</p>
                <div className="flex gap-1 flex-wrap mt-1.5">
                  {job.matched.map((s) => (
                    <span key={s} className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">✓ {s}</span>
                  ))}
                  {job.missing.map((s) => (
                    <span key={s} className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">✗ {s}</span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 overflow-x-hidden">

      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 flex items-center justify-between px-8 py-4 border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm z-20">
        <span className="text-xl font-bold text-brand-500">NeonGrad</span>
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/xCamelot2001/NeonGrad"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-slate-400 hover:text-slate-100 transition-colors hidden sm:block"
          >
            GitHub ↗
          </a>
          <Link
            href="/auth"
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-brand-500 hover:bg-brand-600 transition-colors"
          >
            Get started
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative flex flex-col lg:flex-row items-center gap-12 max-w-6xl mx-auto px-6 pt-36 pb-24">
        {/* Glow blobs */}
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-40 right-1/4 w-64 h-64 bg-purple-500/8 rounded-full blur-3xl pointer-events-none" />

        {/* Copy */}
        <div className="flex-1 relative z-10">
          <div className="inline-block px-3 py-1 mb-6 text-xs font-semibold tracking-wider uppercase text-brand-500 bg-brand-500/10 rounded-full border border-brand-500/20">
            AI-Powered Job Hunting OS
          </div>
          <h1 className="text-5xl lg:text-6xl font-bold leading-tight mb-6">
            NeonGrad finds<br />
            the jobs.{" "}
            <span className="text-brand-500">You land</span>{" "}
            <span className="text-brand-500">them.</span>
          </h1>
          <p className="text-lg text-slate-400 mb-10 leading-relaxed max-w-lg">
            Set your preferences once. Every morning, NeonGrad surfaces your best
            opportunities — ranked by AI-assessed fit, with tailored applications
            ready in 60 seconds.
          </p>
          <div className="flex gap-4 flex-wrap">
            <Link
              href="/auth"
              className="px-7 py-3 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 transition-colors"
            >
              Start for free →
            </Link>
            <a
              href="https://github.com/xCamelot2001/NeonGrad"
              target="_blank"
              rel="noopener noreferrer"
              className="px-7 py-3 font-semibold rounded-xl border border-slate-700 hover:border-slate-500 transition-colors"
            >
              View on GitHub
            </a>
          </div>
        </div>

        {/* Mock dashboard */}
        <div className="flex-1 flex justify-center lg:justify-end relative z-10 w-full">
          <MockDashboard />
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="max-w-5xl mx-auto px-6 py-20 border-t border-slate-800/60">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold mb-3">How it works</h2>
          <p className="text-slate-400">From CV upload to tailored application in three steps.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          {/* Connector line */}
          <div className="hidden md:block absolute top-10 left-1/6 right-1/6 h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent" />

          {HOW_IT_WORKS.map((step) => (
            <div key={step.step} className="relative flex flex-col items-center text-center px-4">
              <div className="w-16 h-16 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-3xl mb-5 relative z-10">
                {step.icon}
              </div>
              <span className="text-xs font-mono text-brand-500/60 mb-1 tracking-widest">{step.step}</span>
              <h3 className="font-semibold text-lg mb-2 text-slate-100">{step.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="max-w-5xl mx-auto px-6 py-20 border-t border-slate-800/60">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold mb-3">Everything you need to graduate job-ready</h2>
          <p className="text-slate-400">Built on production ML and multi-agent AI — not just a job board.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[
            { icon: "🔍", title: "Daily Job Discovery", desc: "Pulls fresh listings from Adzuna every morning. Deduplicated, filtered to your preferences." },
            { icon: "🤖", title: "Fine-tuned Fit Scoring", desc: "sentence-transformers model scores every job against your CV. Gap analysis tells you exactly what you're missing." },
            { icon: "⚡", title: "60-Second Tailoring", desc: "LangGraph agent rewrites your CV bullets and cover letter for a specific JD, with a judge loop for quality." },
            { icon: "🌐", title: "Company Research", desc: "Tavily web search agent fetches mission, culture, and recent news before generating your application." },
            { icon: "📋", title: "Application Kanban", desc: "Track every application through Not Applied → Applied → Interviewing → Offer in one clean board." },
            { icon: "📄", title: "PDF Downloads", desc: "Download your tailored CV and cover letter as polished PDFs, ready to send." },
          ].map((f) => (
            <div
              key={f.title}
              className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 hover:border-brand-500/30 hover:bg-slate-900/70 transition-all"
            >
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-semibold text-base mb-2 text-slate-100">{f.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Tech stack ── */}
      <section className="max-w-4xl mx-auto px-6 py-16 border-t border-slate-800/60 text-center">
        <p className="text-xs font-semibold tracking-widest uppercase text-slate-600 mb-5">Built with</p>
        <div className="flex flex-wrap justify-center gap-2.5">
          {TECH_STACK.map((tech) => (
            <span
              key={tech}
              className="px-3 py-1.5 text-sm rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="relative overflow-hidden border-t border-slate-800/60">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-500/5 via-transparent to-purple-500/5 pointer-events-none" />
        <div className="relative max-w-2xl mx-auto px-6 py-24 text-center">
          <h2 className="text-4xl font-bold mb-4">Ready to job-hunt smarter?</h2>
          <p className="text-slate-400 mb-10 text-lg">
            Join NeonGrad and let AI handle the grind while you focus on the conversations that matter.
          </p>
          <Link
            href="/auth"
            className="inline-block px-10 py-4 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 transition-colors text-lg"
          >
            Get started — it&apos;s free
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-slate-800/60 px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-600 max-w-6xl mx-auto">
        <span className="font-bold text-brand-500/60">NeonGrad</span>
        <p>Built by Hossein &middot; Next.js &middot; FastAPI &middot; LangGraph &middot; Groq &middot; Supabase</p>
        <a
          href="https://github.com/xCamelot2001/NeonGrad"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-slate-400 transition-colors"
        >
          GitHub ↗
        </a>
      </footer>
    </main>
  );
}
