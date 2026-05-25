"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, downloadPdf, streamTailoring } from "@/lib/api";
import Navbar from "@/components/Navbar";

// ── Types ─────────────────────────────────────────────────────────────────────

type AppStatus = "not_applied" | "applied" | "interviewing" | "offer" | "rejected";

const STATUSES: { value: AppStatus; label: string }[] = [
  { value: "not_applied",  label: "Not Applied"  },
  { value: "applied",      label: "Applied"       },
  { value: "interviewing", label: "Interviewing"  },
  { value: "offer",        label: "Offer"         },
  { value: "rejected",     label: "Rejected"      },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function ApplicationDetailPage() {
  const { id }   = useParams();
  const router   = useRouter();
  const stopRef  = useRef<(() => void) | null>(null);

  const [app, setApp]           = useState<any>(null);
  const [tailoring, setTailoring] = useState(false);
  const [tailorLog, setTailorLog] = useState<string[]>([]);
  const [tailorErr, setTailorErr] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<"cv" | "cover_letter" | null>(null);
  const [activeTab, setActiveTab]     = useState<"cv" | "cl">("cv");
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getApplication(id as string).then(setApp).catch(() => {});
  }, [id]);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [tailorLog]);

  // Cleanup SSE stream if user navigates away mid-tailor
  useEffect(() => () => { stopRef.current?.(); }, []);

  async function updateStatus(status: AppStatus) {
    await api.updateStatus(id as string, status);
    setApp((prev: any) => ({ ...prev, status }));
  }

  function handleTailor() {
    if (tailoring) return;
    setTailoring(true);
    setTailorLog([]);
    setTailorErr(null);

    const stop = streamTailoring(id as string, (evt) => {
      if (evt.type === "log") {
        setTailorLog((prev) => [...prev, evt.message ?? ""]);
      }
      if (evt.type === "done") {
        setTailoring(false);
        // Reload to show the tailored docs
        api.getApplication(id as string).then(setApp);
      }
      if (evt.type === "error") {
        setTailorErr(evt.message ?? "Unknown error");
        setTailoring(false);
      }
    });

    stopRef.current = stop;
  }

  async function handleDownload(docType: "cv" | "cover_letter") {
    setDownloading(docType);
    try {
      const company  = app?.job?.company?.replace(/\s+/g, "_") ?? "Company";
      const filename = docType === "cv"
        ? `tailored_cv_${company}.pdf`
        : `cover_letter_${company}.pdf`;
      await downloadPdf(id as string, docType, filename);
    } catch (e: any) {
      alert(`Download failed: ${e.message}`);
    } finally {
      setDownloading(null);
    }
  }

  // ── Loading ──────────────────────────────────────────────────────────────

  if (!app) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-500 animate-pulse">Loading application…</p>
      </main>
    );
  }

  const hasDocs = !!(app.tailored_cv_text || app.cover_letter_text);

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <main className="min-h-screen bg-slate-950">
      <Navbar />

      <div className="max-w-3xl mx-auto px-6 py-10">
        {/* Back */}
        <button
          onClick={() => router.back()}
          className="text-slate-500 hover:text-slate-200 text-sm mb-7 flex items-center gap-1 transition-colors"
        >
          ← Back to applications
        </button>

        {/* Header */}
        <div className="flex items-start justify-between mb-6 gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">{app.job?.title}</h1>
            <p className="text-slate-400 mt-1">
              {app.job?.company}
              {app.job?.location ? ` · ${app.job.location}` : ""}
            </p>
          </div>
          {app.job?.url && (
            <a
              href={app.job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-brand-400 hover:text-brand-300 border border-brand-500/30 hover:border-brand-400 rounded-lg px-3 py-1.5 transition-colors whitespace-nowrap"
              onClick={(e) => e.stopPropagation()}
            >
              View posting ↗
            </a>
          )}
        </div>

        {/* Status bar */}
        <div className="flex flex-wrap gap-2 mb-8">
          {STATUSES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => updateStatus(value)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                app.status === value
                  ? "bg-brand-600 border-brand-500 text-white font-medium"
                  : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ── Generate button ── */}
        {!hasDocs && !tailoring && (
          <button
            onClick={handleTailor}
            className="w-full py-3.5 font-semibold rounded-xl bg-brand-600 hover:bg-brand-500 text-white transition-colors mb-6 text-sm"
          >
            ⚡ Generate tailored CV + Cover Letter
          </button>
        )}

        {/* Re-generate (already have docs) */}
        {hasDocs && !tailoring && (
          <button
            onClick={handleTailor}
            className="w-full py-2.5 font-medium rounded-xl border border-slate-700 hover:border-brand-500/50 text-slate-400 hover:text-slate-200 transition-colors mb-6 text-sm"
          >
            ↺ Re-generate documents
          </button>
        )}

        {/* Tailoring in progress */}
        {tailoring && (
          <div className="mb-6 rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
              <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
              <span className="text-sm font-medium text-slate-300">Agent running…</span>
            </div>
            <div className="p-4 font-mono text-xs text-slate-400 space-y-1.5 max-h-48 overflow-y-auto">
              {tailorLog.map((line, i) => (
                <div key={i} className="leading-relaxed">{line}</div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        )}

        {/* Error */}
        {tailorErr && (
          <div className="mb-6 p-4 rounded-xl bg-red-950/40 border border-red-900 text-red-400 text-sm">
            ⚠️ {tailorErr}
          </div>
        )}

        {/* ── Documents ── */}
        {hasDocs && (
          <div className="space-y-6">
            {/* Tabs */}
            <div className="flex gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800">
              {(["cv", "cl"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 py-2 text-sm rounded-lg font-medium transition-colors ${
                    activeTab === tab
                      ? "bg-brand-600 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab === "cv" ? "📄 Tailored CV" : "💌 Cover Letter"}
                </button>
              ))}
            </div>

            {/* CV tab */}
            {activeTab === "cv" && app.tailored_cv_text && (
              <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
                  <span className="text-sm font-medium text-slate-300">Tailored CV</span>
                  <button
                    onClick={() => handleDownload("cv")}
                    disabled={downloading === "cv"}
                    className="text-xs text-brand-400 hover:text-brand-300 border border-brand-500/30 hover:border-brand-400 rounded-lg px-3 py-1 transition-colors disabled:opacity-50"
                  >
                    {downloading === "cv" ? "Generating…" : "⬇ Download PDF"}
                  </button>
                </div>
                <pre className="p-5 text-slate-300 text-sm whitespace-pre-wrap leading-relaxed font-sans max-h-[500px] overflow-y-auto">
                  {app.tailored_cv_text}
                </pre>
              </div>
            )}

            {/* Cover letter tab */}
            {activeTab === "cl" && app.cover_letter_text && (
              <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
                  <span className="text-sm font-medium text-slate-300">Cover Letter</span>
                  <button
                    onClick={() => handleDownload("cover_letter")}
                    disabled={downloading === "cover_letter"}
                    className="text-xs text-brand-400 hover:text-brand-300 border border-brand-500/30 hover:border-brand-400 rounded-lg px-3 py-1 transition-colors disabled:opacity-50"
                  >
                    {downloading === "cover_letter" ? "Generating…" : "⬇ Download PDF"}
                  </button>
                </div>
                <pre className="p-5 text-slate-300 text-sm whitespace-pre-wrap leading-relaxed font-sans max-h-[500px] overflow-y-auto">
                  {app.cover_letter_text}
                </pre>
              </div>
            )}

            {/* Tailored-at timestamp */}
            {app.tailored_at && (
              <p className="text-xs text-slate-600 text-right">
                Generated {new Date(app.tailored_at).toLocaleString()}
              </p>
            )}
          </div>
        )}

        {/* ── Interview prep CTA ── */}
        {app.status === "interviewing" && (
          <Link
            href={`/applications/${id}/prep`}
            className="block mt-8 text-center py-3.5 font-semibold rounded-xl border border-brand-500 text-brand-400 hover:bg-brand-600 hover:text-white hover:border-brand-600 transition-all"
          >
            🎯 Generate Interview Prep →
          </Link>
        )}
      </div>
    </main>
  );
}
