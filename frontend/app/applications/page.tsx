"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

type AppStatus = "not_applied" | "applied" | "interviewing" | "offer" | "rejected";

interface Application {
  id: string;
  status: AppStatus;
  tailored_cv_text?: string | null;
  tailored_at?: string | null;
  updated_at: string;
  job: {
    title: string;
    company: string;
    location?: string;
    url?: string;
  };
}

// ── Column config ─────────────────────────────────────────────────────────────

const COLUMNS: { status: AppStatus; label: string; color: string; dot: string }[] = [
  { status: "not_applied",  label: "Not Applied",  color: "border-slate-700",  dot: "bg-slate-500"  },
  { status: "applied",      label: "Applied",      color: "border-blue-700",   dot: "bg-blue-400"   },
  { status: "interviewing", label: "Interviewing", color: "border-yellow-600", dot: "bg-yellow-400" },
  { status: "offer",        label: "Offer",        color: "border-green-700",  dot: "bg-green-400"  },
  { status: "rejected",     label: "Rejected",     color: "border-red-900",    dot: "bg-red-500"    },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ApplicationsPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading]           = useState(true);
  const [movingId, setMovingId]         = useState<string | null>(null);

  useEffect(() => {
    api.getApplications()
      .then((d) => setApplications(d.applications ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function moveStatus(app: Application, newStatus: AppStatus) {
    if (app.status === newStatus) return;
    setMovingId(app.id);
    try {
      await api.updateStatus(app.id, newStatus);
      setApplications((prev) =>
        prev.map((a) => (a.id === app.id ? { ...a, status: newStatus } : a))
      );
    } catch { /* noop */ } finally {
      setMovingId(null);
    }
  }

  const byStatus = (status: AppStatus) =>
    applications.filter((a) => a.status === status);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-500 animate-pulse">Loading applications…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-4 border-b border-slate-800">
        <span className="text-xl font-bold text-brand-500">NeonGrad</span>
        <div className="flex gap-6 text-sm text-slate-400">
          <Link href="/dashboard"    className="hover:text-slate-100">Dashboard</Link>
          <Link href="/applications" className="text-slate-100 font-medium">Applications</Link>
          <Link href="/profile"      className="hover:text-slate-100">Profile</Link>
        </div>
      </nav>

      {/* Header */}
      <div className="px-6 pt-8 pb-4 flex items-center justify-between max-w-[1400px] mx-auto">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Application Tracker</h1>
          <p className="text-slate-500 text-sm mt-1">
            {applications.length} application{applications.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <Link
          href="/dashboard"
          className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
        >
          + Add from dashboard →
        </Link>
      </div>

      {/* Empty state */}
      {applications.length === 0 && (
        <div className="max-w-md mx-auto mt-20 text-center px-6">
          <div className="text-5xl mb-5">📋</div>
          <h2 className="text-lg font-semibold text-slate-200 mb-2">No applications yet</h2>
          <p className="text-slate-500 text-sm mb-6">
            Open a job card on the dashboard and click{" "}
            <span className="text-brand-400">"Generate tailored CV"</span> to create your first application.
          </p>
          <Link
            href="/dashboard"
            className="inline-block px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold transition-colors"
          >
            Go to Dashboard
          </Link>
        </div>
      )}

      {/* Kanban board */}
      {applications.length > 0 && (
        <div className="overflow-x-auto pb-12">
          <div className="flex gap-4 px-6 pt-2 min-w-max max-w-[1400px] mx-auto">
            {COLUMNS.map(({ status, label, color, dot }) => {
              const cards = byStatus(status);
              return (
                <div key={status} className="w-64 flex-shrink-0">
                  {/* Column header */}
                  <div className="flex items-center gap-2 mb-3 px-1">
                    <span className={`w-2 h-2 rounded-full ${dot}`} />
                    <span className="text-sm font-semibold text-slate-300">{label}</span>
                    <span className="ml-auto text-xs text-slate-600 bg-slate-800 rounded-full px-2 py-0.5">
                      {cards.length}
                    </span>
                  </div>

                  {/* Column body */}
                  <div
                    className={`rounded-2xl border ${color} bg-slate-900/50 min-h-[200px] p-2 space-y-2`}
                  >
                    {cards.length === 0 && (
                      <div className="h-24 flex items-center justify-center text-slate-700 text-xs">
                        Empty
                      </div>
                    )}
                    {cards.map((app) => (
                      <KanbanCard
                        key={app.id}
                        app={app}
                        isMoving={movingId === app.id}
                        onMove={moveStatus}
                        onClick={() => router.push(`/applications/${app.id}`)}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </main>
  );
}

// ── Kanban card ───────────────────────────────────────────────────────────────

function KanbanCard({
  app,
  isMoving,
  onMove,
  onClick,
}: {
  app: Application;
  isMoving: boolean;
  onMove: (app: Application, status: AppStatus) => void;
  onClick: () => void;
}) {
  const [showMove, setShowMove] = useState(false);
  const nextStatuses = COLUMNS.filter((c) => c.status !== app.status);

  return (
    <div
      className={`rounded-xl bg-slate-900 border border-slate-800 p-3 cursor-pointer
        hover:border-brand-500/40 transition-all group relative select-none
        ${isMoving ? "opacity-50 pointer-events-none" : ""}`}
      onClick={onClick}
    >
      {/* Title + company */}
      <p className="text-sm font-medium text-slate-100 leading-snug line-clamp-2 pr-6">
        {app.job?.title ?? "Untitled"}
      </p>
      <p className="text-xs text-slate-500 mt-0.5 truncate">
        {app.job?.company}
        {app.job?.location ? ` · ${app.job.location}` : ""}
      </p>

      {/* Tailored badge */}
      <div className="mt-2">
        {app.tailored_cv_text ? (
          <span className="text-[10px] text-green-400 bg-green-950/60 border border-green-900 rounded-full px-2 py-0.5">
            ✓ Tailored
          </span>
        ) : (
          <span className="text-[10px] text-slate-600 bg-slate-800 rounded-full px-2 py-0.5">
            Draft
          </span>
        )}
      </div>

      {/* Move button — revealed on hover */}
      <div
        className="absolute top-2.5 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={(e) => {
          e.stopPropagation();
          setShowMove((v) => !v);
        }}
      >
        <button className="w-6 h-6 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-xs flex items-center justify-center">
          ↕
        </button>
      </div>

      {/* Status picker */}
      {showMove && (
        <div
          className="absolute top-9 right-2 z-20 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden w-40"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="text-[10px] text-slate-500 px-3 pt-2 pb-1 uppercase tracking-wider font-medium">
            Move to
          </p>
          {nextStatuses.map(({ status, label, dot }) => (
            <button
              key={status}
              className="flex items-center gap-2 w-full px-3 py-2 text-xs text-slate-300 hover:bg-slate-700 transition-colors text-left"
              onClick={() => {
                setShowMove(false);
                onMove(app, status);
              }}
            >
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot}`} />
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
