"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

export default function JobDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [job, setJob] = useState<any>(null);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/jobs/${id}`)
      .then((r) => r.json())
      .then(setJob)
      .catch(() => {});
  }, [id]);

  async function handleApply() {
    setApplying(true);
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/applications`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: id }),
    });
    const data = await res.json();
    router.push(`/applications/${data.id}`);
  }

  if (!job) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-500">Loading job details…</p>
      </main>
    );
  }

  const score = Math.round((job.relevance_score ?? 0) * 100);

  return (
    <main className="min-h-screen bg-slate-950">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <button onClick={() => router.back()} className="text-slate-400 hover:text-slate-100 text-sm mb-6">
          ← Back
        </button>

        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold mb-1">{job.title}</h1>
            <p className="text-slate-400">{job.company} · {job.location}</p>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-brand-500">{score}%</div>
            <div className="text-slate-500 text-sm">fit score</div>
          </div>
        </div>

        {/* Gap analysis */}
        {job.gap_analysis && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="p-4 rounded-xl bg-green-500/5 border border-green-500/20">
              <h3 className="text-sm font-semibold text-green-400 mb-2">You have ✓</h3>
              <ul className="space-y-1">
                {job.gap_analysis.matched_skills.map((s: string) => (
                  <li key={s} className="text-sm text-slate-300">{s}</li>
                ))}
              </ul>
            </div>
            <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20">
              <h3 className="text-sm font-semibold text-red-400 mb-2">You're missing ✗</h3>
              <ul className="space-y-1">
                {job.gap_analysis.missing_skills.map((s: string) => (
                  <li key={s} className="text-sm text-slate-300">{s}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* JD */}
        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 mb-6">
          <h3 className="font-semibold mb-3">Job Description</h3>
          <p className="text-slate-400 text-sm whitespace-pre-line leading-relaxed">{job.jd_raw}</p>
        </div>

        <div className="flex gap-4">
          <button
            onClick={handleApply}
            disabled={applying}
            className="flex-1 py-3 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 transition-colors"
          >
            {applying ? "Creating application…" : "⚡ Generate Application"}
          </button>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 font-semibold rounded-xl border border-slate-700 hover:border-slate-500 transition-colors"
          >
            View original →
          </a>
        </div>
      </div>
    </main>
  );
}
