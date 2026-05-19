"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

const STATUSES = ["not_applied", "applied", "interviewing", "offer", "rejected"];
const STATUS_LABELS: Record<string, string> = {
  not_applied: "Not Applied",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer",
  rejected: "Rejected",
};
const STATUS_COLORS: Record<string, string> = {
  not_applied: "text-slate-400",
  applied: "text-blue-400",
  interviewing: "text-yellow-400",
  offer: "text-green-400",
  rejected: "text-red-400",
};

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getApplications()
      .then((d) => setApplications(d.applications ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="min-h-screen bg-slate-950">
      <nav className="flex items-center justify-between px-8 py-4 border-b border-slate-800">
        <span className="text-xl font-bold text-brand-500">NeonGrad</span>
        <div className="flex gap-6 text-sm text-slate-400">
          <Link href="/dashboard" className="hover:text-slate-100">Dashboard</Link>
          <Link href="/applications" className="text-slate-100">Applications</Link>
          <Link href="/profile" className="hover:text-slate-100">Profile</Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold mb-8">Applications</h1>

        {loading ? (
          <p className="text-slate-500">Loading…</p>
        ) : applications.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-slate-800 rounded-2xl">
            <div className="text-4xl mb-4">📋</div>
            <p className="text-slate-400">No applications yet — generate one from a job card.</p>
            <Link href="/dashboard" className="inline-block mt-4 text-brand-500 hover:underline text-sm">
              Go to dashboard →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {applications.map((app) => (
              <Link key={app.id} href={`/applications/${app.id}`}>
                <div className="flex items-center justify-between p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-brand-500/40 transition-colors cursor-pointer">
                  <div>
                    <p className="font-medium">{app.job?.title ?? "Untitled job"}</p>
                    <p className="text-slate-400 text-sm">{app.job?.company} · {app.job?.location}</p>
                  </div>
                  <span className={`text-sm font-medium ${STATUS_COLORS[app.status]}`}>
                    {STATUS_LABELS[app.status]}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
