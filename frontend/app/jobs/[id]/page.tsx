"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";

const STRATEGY_CFG: Record<string, { label: string; pill: string; ring: string; ringBg: string }> = {
  strong_match: {
    label: "Strong match",
    pill: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    ring: "#10b981",
    ringBg: "bg-emerald-500/10",
  },
  decent: {
    label: "Decent fit",
    pill: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    ring: "#3b82f6",
    ringBg: "bg-blue-500/10",
  },
  stretch: {
    label: "Stretch",
    pill: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    ring: "#f59e0b",
    ringBg: "bg-amber-500/10",
  },
  skip: {
    label: "Skip",
    pill: "bg-slate-600/20 text-slate-500 border-slate-600/30",
    ring: "#475569",
    ringBg: "bg-slate-700/10",
  },
};

const GAP_SEVERITY_LABEL: Record<string, string> = {
  none: "No significant gaps",
  low: "Minor gaps",
  medium: "Moderate gaps",
  high: "Significant gaps",
  unknown: "Gap unknown",
};

const GAP_SEVERITY_COLOR: Record<string, string> = {
  none: "text-emerald-400",
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-red-400",
  unknown: "text-slate-500",
};

export default function JobDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [job, setJob] = useState<any>(null);
  const [applying, setApplying] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getJob(id as string)
      .then(setJob)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  async function handleApply() {
    setApplying(true);
    try {
      const data = await api.createApplication(id as string);
      router.push(`/applications/${data.id}`);
    } catch {
      setApplying(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-500">Loading job details…</p>
      </main>
    );
  }

  if (!job) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-500">Job not found.</p>
      </main>
    );
  }

  const score = job.relevance_score != null ? Math.round(job.relevance_score * 100) : null;
  const strategy = job.strategy ?? "unranked";
  const cfg = STRATEGY_CFG[strategy];
  const gap = job.gap_analysis ?? null;
  const matched: string[] = gap?.matched_skills ?? [];
  const missing: string[] = gap?.missing_skills ?? [];
  const gapSeverity: string = gap?.gap_severity ?? "unknown";
  const jdStructured = job.jd_structured ?? null;
  const requiredSkills: string[] = jdStructured?.required_skills ?? [];
  const techStack: string[] = jdStructured?.tech_stack ?? [];
  const niceToHaves: string[] = jdStructured?.nice_to_haves ?? [];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto px-6 py-10">
        {/* Back */}
        <button
          onClick={() => router.back()}
          className="text-slate-500 hover:text-slate-300 text-sm mb-8 transition-colors"
        >
          ← Back to dashboard
        </button>

        {/* Title row */}
        <div className="flex items-start gap-6 mb-8">
          {/* Score ring */}
          {score != null && cfg ? (
            <div className="shrink-0 flex flex-col items-center gap-1">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center"
                style={{
                  background: `conic-gradient(${cfg.ring} ${score * 3.6}deg, #1e293b 0deg)`,
                }}
              >
                <div className="w-14 h-14 rounded-full bg-slate-950 flex items-center justify-center flex-col">
                  <span className="text-lg font-bold leading-none">{score}%</span>
                  <span className="text-xs text-slate-600 leading-none mt-0.5">fit</span>
                </div>
              </div>
            </div>
          ) : null}

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap mb-1">
              <h1 className="text-2xl font-bold">{job.title}</h1>
              {cfg && (
                <span className={`text-xs px-2.5 py-1 rounded-full border ${cfg.pill}`}>
                  {cfg.label}
                </span>
              )}
            </div>
            <p className="text-slate-400">
              {job.company}
              {job.location && <span className="text-slate-600"> · {job.location}</span>}
            </p>
            {job.strategy_reasoning && (
              <p className="text-slate-500 text-sm mt-2">{job.strategy_reasoning}</p>
            )}
          </div>
        </div>

        {/* Gap analysis panel */}
        {(matched.length > 0 || missing.length > 0) && (
          <div className="mb-6 rounded-2xl border border-slate-800 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
              <h2 className="font-semibold text-sm">Skill gap analysis</h2>
              <span className={`text-xs font-medium ${GAP_SEVERITY_COLOR[gapSeverity]}`}>
                {GAP_SEVERITY_LABEL[gapSeverity]}
              </span>
            </div>
            <div className="grid grid-cols-2 divide-x divide-slate-800">
              <div className="p-5">
                <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wide mb-3">
                  You have ✓
                </p>
                {matched.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {matched.map((s) => (
                      <span
                        key={s}
                        className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-600 text-sm">No matched skills found.</p>
                )}
              </div>
              <div className="p-5">
                <p className="text-xs font-semibold text-red-400 uppercase tracking-wide mb-3">
                  You're missing ✗
                </p>
                {missing.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {missing.map((s) => (
                      <span
                        key={s}
                        className="text-xs px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-600 text-sm">No critical gaps identified.</p>
                )}
              </div>
            </div>
            {gap?.summary && (
              <div className="px-5 py-3 border-t border-slate-800 bg-slate-900/40">
                <p className="text-slate-400 text-sm">{gap.summary}</p>
              </div>
            )}
          </div>
        )}

        {/* JD structured skills */}
        {(requiredSkills.length > 0 || techStack.length > 0) && (
          <div className="mb-6 p-5 rounded-2xl border border-slate-800 bg-slate-900/40">
            <h2 className="font-semibold text-sm mb-4">What they're looking for</h2>
            <div className="space-y-3">
              {requiredSkills.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Required skills</p>
                  <div className="flex flex-wrap gap-2">
                    {requiredSkills.map((s) => (
                      <span key={s} className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {techStack.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Tech stack</p>
                  <div className="flex flex-wrap gap-2">
                    {techStack.map((s) => (
                      <span key={s} className="text-xs px-2.5 py-1 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {niceToHaves.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Nice to haves</p>
                  <div className="flex flex-wrap gap-2">
                    {niceToHaves.map((s) => (
                      <span key={s} className="text-xs px-2.5 py-1 rounded-full bg-slate-800/60 text-slate-400 border border-slate-700/60">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Raw JD */}
        {job.jd_raw && (
          <div className="mb-8 p-5 rounded-2xl border border-slate-800 bg-slate-900/40">
            <h2 className="font-semibold text-sm mb-3">Job description</h2>
            <p className="text-slate-400 text-sm whitespace-pre-line leading-relaxed">
              {job.jd_raw}
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleApply}
            disabled={applying}
            className="flex-1 py-3 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 transition-colors"
          >
            {applying ? "Creating application…" : "⚡ Generate Application"}
          </button>
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-5 py-3 font-semibold rounded-xl border border-slate-700 hover:border-slate-500 transition-colors"
            >
              View original →
            </a>
          )}
        </div>
      </div>
    </main>
  );
}
