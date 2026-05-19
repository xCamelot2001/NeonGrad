"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface JobRanking {
  job_id: string;
  title: string;
  company: string;
  location: string;
  relevance_score: number;
  strategy: "strong_match" | "decent" | "stretch" | "skip";
  strategy_reasoning: string;
  gap_analysis: {
    matched_skills: string[];
    missing_skills: string[];
    gap_severity: "low" | "medium" | "high";
  };
  url: string;
}

const STRATEGY_BADGE: Record<string, { label: string; className: string }> = {
  strong_match: { label: "Strong match", className: "bg-green-500/20 text-green-400 border-green-500/30" },
  decent: { label: "Decent", className: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  stretch: { label: "Stretch", className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  skip: { label: "Skip", className: "bg-red-500/20 text-red-400 border-red-500/30" },
  unranked: { label: "New", className: "bg-slate-500/20 text-slate-400 border-slate-500/30" },
};

export default function DashboardPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function fetchRankedJobs() {
    try {
      const data = await api.getRankedJobs();
      setJobs(data.jobs ?? []);
    } catch {
      // Not authed or API down — show empty state
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    await api.discoverJobs();
    await fetchRankedJobs();
    setRefreshing(false);
  }

  useEffect(() => {
    fetchRankedJobs();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950">
      {/* Header */}
      <nav className="flex items-center justify-between px-8 py-4 border-b border-slate-800">
        <span className="text-xl font-bold text-brand-500">NeonGrad</span>
        <div className="flex gap-6 text-sm text-slate-400">
          <Link href="/dashboard" className="text-slate-100">Dashboard</Link>
          <Link href="/applications" className="hover:text-slate-100">Applications</Link>
          <Link href="/profile" className="hover:text-slate-100">Profile</Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Top stats */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">Today's Jobs</h1>
            <p className="text-slate-400 text-sm mt-1">
              {jobs.length} jobs ranked for you
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-5 py-2.5 text-sm font-medium rounded-lg bg-brand-500 hover:bg-brand-600 disabled:opacity-50 transition-colors"
          >
            {refreshing ? "Refreshing…" : "↻ Refresh jobs"}
          </button>
        </div>

        {/* Job cards */}
        {loading ? (
          <div className="text-center text-slate-500 py-20">Loading your ranked jobs…</div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-slate-800 rounded-2xl">
            <div className="text-4xl mb-4">🔍</div>
            <p className="text-slate-400">No jobs yet — click Refresh to run job discovery.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => {
              const badge = STRATEGY_BADGE[job.strategy] ?? STRATEGY_BADGE.unranked;
              const score = job.relevance_score != null ? Math.round(job.relevance_score * 100) : null;
              return (
                <div
                  key={job.job_id}
                  onClick={() => router.push(`/jobs/${job.job_id}`)}
                  className="p-6 rounded-2xl border border-slate-800 bg-slate-900 hover:border-brand-500/40 transition-colors cursor-pointer"
                >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="font-semibold text-lg truncate">{job.title}</h3>
                          <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full border ${badge.className}`}>
                            {badge.label}
                          </span>
                          {job.url && (
                            <a
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="shrink-0 text-xs px-2 py-0.5 rounded-full border border-slate-700 text-slate-400 hover:text-brand-400 hover:border-brand-500/40 transition-colors"
                            >
                              View job ↗
                            </a>
                          )}
                        </div>
                        <p className="text-slate-400 text-sm">{job.company} · {job.location}</p>
                        <p className="text-slate-500 text-sm mt-2 line-clamp-1">{job.strategy_reasoning}</p>
                      </div>
                      {/* Score circle — only shown once ranked */}
                      {score != null && (
                        <div className="shrink-0 flex flex-col items-center">
                          <div
                            className="w-14 h-14 rounded-full flex items-center justify-center text-lg font-bold"
                            style={{
                              background: `conic-gradient(#4f6ef7 ${score * 3.6}deg, #1e293b 0deg)`,
                            }}
                          >
                            <div className="w-10 h-10 rounded-full bg-slate-900 flex items-center justify-center text-sm font-bold">
                              {score}%
                            </div>
                          </div>
                          <span className="text-xs text-slate-500 mt-1">fit</span>
                        </div>
                      )}
                    </div>

                    {/* Skills */}
                    {job.gap_analysis && (
                      <div className="flex gap-2 flex-wrap mt-3">
                        {job.gap_analysis.matched_skills.slice(0, 4).map((s) => (
                          <span key={s} className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
                            ✓ {s}
                          </span>
                        ))}
                        {job.gap_analysis.missing_skills.slice(0, 2).map((s) => (
                          <span key={s} className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                            ✗ {s}
                          </span>
                        ))}
                      </div>
                    )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
