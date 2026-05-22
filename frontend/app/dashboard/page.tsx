"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface GapAnalysis {
  matched_skills: string[];
  missing_skills: string[];
  gap_severity: "none" | "low" | "medium" | "high" | "unknown";
  summary?: string;
}

interface JobRanking {
  job_id: string;
  title: string;
  company: string;
  location: string;
  relevance_score: number | null;
  strategy: "strong_match" | "decent" | "stretch" | "skip" | "unranked";
  strategy_reasoning: string | null;
  gap_analysis: GapAnalysis | null;
  url: string;
}

// ─── Config ──────────────────────────────────────────────────────────────────

const BADGE: Record<string, { label: string; pill: string; ring: string; score: string }> = {
  strong_match: {
    label: "Strong match",
    pill: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    ring: "#10b981",
    score: "text-emerald-400",
  },
  decent: {
    label: "Decent",
    pill: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    ring: "#3b82f6",
    score: "text-blue-400",
  },
  stretch: {
    label: "Stretch",
    pill: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    ring: "#f59e0b",
    score: "text-amber-400",
  },
  skip: {
    label: "Skip",
    pill: "bg-slate-600/20 text-slate-500 border-slate-600/30",
    ring: "#475569",
    score: "text-slate-500",
  },
  unranked: {
    label: "Unranked",
    pill: "bg-slate-700/20 text-slate-400 border-slate-700/30",
    ring: "#334155",
    score: "text-slate-400",
  },
};

const TABS = [
  { key: "all", label: "All" },
  { key: "strong_match", label: "Strong match" },
  { key: "decent", label: "Decent" },
  { key: "stretch", label: "Stretch" },
  { key: "skip", label: "Skip" },
] as const;

type Tab = (typeof TABS)[number]["key"];

// ─── Score ring ───────────────────────────────────────────────────────────────

function ScoreRing({ score, strategy }: { score: number; strategy: string }) {
  const pct = Math.round(score * 100);
  const deg = score * 360;
  const cfg = BADGE[strategy] ?? BADGE.unranked;
  return (
    <div className="shrink-0 flex flex-col items-center gap-1">
      <div
        className="w-14 h-14 rounded-full flex items-center justify-center"
        style={{
          background: `conic-gradient(${cfg.ring} ${deg}deg, #1e293b 0deg)`,
        }}
      >
        <div className="w-10 h-10 rounded-full bg-slate-900 flex items-center justify-center">
          <span className={`text-sm font-bold ${cfg.score}`}>{pct}%</span>
        </div>
      </div>
      <span className="text-xs text-slate-600">fit</span>
    </div>
  );
}

// ─── Stat bar ─────────────────────────────────────────────────────────────────

function StatBar({ jobs }: { jobs: JobRanking[] }) {
  const counts = {
    strong_match: jobs.filter((j) => j.strategy === "strong_match").length,
    decent: jobs.filter((j) => j.strategy === "decent").length,
    stretch: jobs.filter((j) => j.strategy === "stretch").length,
    total: jobs.length,
  };
  return (
    <div className="grid grid-cols-3 gap-4 mb-8">
      {[
        { label: "Strong match", count: counts.strong_match, color: "text-emerald-400", bg: "bg-emerald-500/10" },
        { label: "Decent fit", count: counts.decent, color: "text-blue-400", bg: "bg-blue-500/10" },
        { label: "Stretch", count: counts.stretch, color: "text-amber-400", bg: "bg-amber-500/10" },
      ].map(({ label, count, color, bg }) => (
        <div key={label} className={`rounded-xl border border-slate-800 p-4 ${bg}`}>
          <p className={`text-2xl font-bold ${color}`}>{count}</p>
          <p className="text-xs text-slate-500 mt-0.5">{label}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Job card ─────────────────────────────────────────────────────────────────

function JobCard({ job, onClick }: { job: JobRanking; onClick: () => void }) {
  const cfg = BADGE[job.strategy] ?? BADGE.unranked;
  const score = job.relevance_score;
  const gap = job.gap_analysis;
  const matched = gap?.matched_skills?.slice(0, 4) ?? [];
  const missing = gap?.missing_skills?.slice(0, 2) ?? [];

  return (
    <div
      onClick={onClick}
      className="group p-5 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900 transition-all cursor-pointer"
    >
      <div className="flex items-start gap-4">
        {/* Score ring */}
        {score != null ? (
          <ScoreRing score={score} strategy={job.strategy} />
        ) : (
          <div className="shrink-0 w-14 h-14 rounded-full border-2 border-dashed border-slate-700 flex items-center justify-center">
            <span className="text-xs text-slate-600">—</span>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <h3 className="font-semibold text-base truncate">{job.title}</h3>
            <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full border ${cfg.pill}`}>
              {cfg.label}
            </span>
            {job.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="shrink-0 text-xs px-2 py-0.5 rounded-full border border-slate-700/60 text-slate-500 hover:text-brand-400 hover:border-brand-500/40 transition-colors"
              >
                View ↗
              </a>
            )}
          </div>
          <p className="text-slate-400 text-sm">
            {job.company}
            {job.location && <span className="text-slate-600"> · {job.location}</span>}
          </p>

          {/* Strategy reasoning */}
          {job.strategy_reasoning && job.strategy !== "unranked" && (
            <p className="text-slate-500 text-xs mt-2 line-clamp-1">{job.strategy_reasoning}</p>
          )}

          {/* Skill chips */}
          {(matched.length > 0 || missing.length > 0) && (
            <div className="flex gap-1.5 flex-wrap mt-2.5">
              {matched.map((s) => (
                <span
                  key={s}
                  className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  ✓ {s}
                </span>
              ))}
              {missing.map((s) => (
                <span
                  key={s}
                  className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20"
                >
                  ✗ {s}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [ranking, setRanking] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("all");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  async function loadJobs() {
    try {
      const data = await api.getRankedJobs(100);
      setJobs(data.jobs ?? []);
    } catch {
      // silently fail — user may not be authed yet
    } finally {
      setLoading(false);
    }
  }

  async function handleDiscover() {
    setDiscovering(true);
    setStatusMsg("Fetching fresh jobs from Adzuna…");
    try {
      const result = await api.discoverJobs();
      const n = result.new_jobs ?? 0;
      setStatusMsg(`Found ${n} new job${n !== 1 ? "s" : ""}. Reloading…`);
      await loadJobs();
    } catch {
      setStatusMsg("Discovery failed — try again.");
    } finally {
      setDiscovering(false);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  }

  async function handleRank() {
    setRanking(true);
    setStatusMsg("Ranking jobs with AI — this takes ~30 seconds…");
    try {
      const result = await api.rankJobs();
      const n = result.ranked ?? 0;
      setStatusMsg(`Ranked ${n} job${n !== 1 ? "s" : ""}. Reloading…`);
      await loadJobs();
    } catch {
      setStatusMsg("Ranking failed — try again.");
    } finally {
      setRanking(false);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  }

  useEffect(() => {
    loadJobs();
  }, []);

  const visibleJobs =
    activeTab === "all" ? jobs : jobs.filter((j) => j.strategy === activeTab);

  const unrankedCount = jobs.filter((j) => j.strategy === "unranked").length;

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-4 border-b border-slate-800 sticky top-0 z-10 bg-slate-950/80 backdrop-blur">
        <span className="text-xl font-bold text-brand-500">NeonGrad</span>
        <div className="flex gap-6 text-sm text-slate-400">
          <Link href="/dashboard" className="text-slate-100 font-medium">Dashboard</Link>
          <Link href="/applications" className="hover:text-slate-100 transition-colors">Applications</Link>
          <Link href="/profile" className="hover:text-slate-100 transition-colors">Profile</Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Header row */}
        <div className="flex items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Job Rankings</h1>
            <p className="text-slate-400 text-sm mt-1">
              {jobs.length > 0
                ? `${jobs.length} jobs · ${unrankedCount > 0 ? `${unrankedCount} awaiting ranking` : "all ranked"}`
                : "No jobs yet"}
            </p>
          </div>
          <div className="flex gap-2.5">
            <button
              onClick={handleDiscover}
              disabled={discovering || ranking}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-700 hover:border-slate-600 hover:bg-slate-800 disabled:opacity-40 transition-all"
            >
              {discovering ? "Fetching…" : "↻ Discover"}
            </button>
            <button
              onClick={handleRank}
              disabled={ranking || discovering}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-brand-500 hover:bg-brand-600 disabled:opacity-40 transition-all"
            >
              {ranking ? "Ranking…" : "⚡ Rank Jobs"}
            </button>
          </div>
        </div>

        {/* Status banner */}
        {statusMsg && (
          <div className="mb-6 px-4 py-3 rounded-lg bg-brand-500/10 border border-brand-500/20 text-sm text-brand-300">
            {statusMsg}
          </div>
        )}

        {/* Stat bar */}
        {jobs.length > 0 && <StatBar jobs={jobs} />}

        {/* Filter tabs */}
        {jobs.length > 0 && (
          <div className="flex gap-1.5 mb-6 border-b border-slate-800 pb-4">
            {TABS.map((tab) => {
              const count = tab.key === "all" ? jobs.length : jobs.filter((j) => j.strategy === tab.key).length;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    activeTab === tab.key
                      ? "bg-brand-500/20 text-brand-400 font-medium"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {tab.label}
                  <span className="ml-1.5 text-xs opacity-60">{count}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Job list */}
        {loading ? (
          <div className="text-center text-slate-500 py-24">Loading your ranked jobs…</div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-24 border border-dashed border-slate-800 rounded-2xl">
            <div className="text-5xl mb-4">🔍</div>
            <p className="text-slate-400 mb-2">No jobs yet.</p>
            <p className="text-slate-600 text-sm">Click ↻ Discover to pull fresh listings, then ⚡ Rank Jobs to score them.</p>
          </div>
        ) : visibleJobs.length === 0 ? (
          <div className="text-center py-16 text-slate-600 text-sm">
            No {activeTab.replace("_", " ")} jobs in your current batch.
          </div>
        ) : (
          <div className="space-y-3">
            {visibleJobs.map((job) => (
              <JobCard
                key={job.job_id}
                job={job}
                onClick={() => router.push(`/jobs/${job.job_id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
