"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

const STATUSES = ["not_applied", "applied", "interviewing", "offer", "rejected"];

export default function ApplicationDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [app, setApp] = useState<any>(null);
  const [tailoring, setTailoring] = useState(false);
  const [tailorLog, setTailorLog] = useState<string[]>([]);

  useEffect(() => {
    api.getApplication(id as string).then(setApp).catch(() => {});
  }, [id]);

  async function updateStatus(status: string) {
    await api.updateStatus(id as string, status);
    setApp({ ...app, status });
  }

  async function handleTailor() {
    setTailoring(true);
    setTailorLog([]);
    // SSE streaming
    const es = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL}/api/applications/${id}/tailor`
    );
    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "log") setTailorLog((prev) => [...prev, data.message]);
      if (data.type === "done") {
        es.close();
        setTailoring(false);
        // Reload to show tailored docs
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/applications/${id}`)
          .then((r) => r.json())
          .then(setApp);
      }
    };
    es.onerror = () => { es.close(); setTailoring(false); };
  }

  if (!app) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-500">Loading application…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <button onClick={() => router.back()} className="text-slate-400 hover:text-slate-100 text-sm mb-6">
          ← Back
        </button>

        <h1 className="text-2xl font-bold mb-1">{app.job?.title}</h1>
        <p className="text-slate-400 mb-6">{app.job?.company}</p>

        {/* Status selector */}
        <div className="flex gap-2 mb-8 flex-wrap">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => updateStatus(s)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                app.status === s
                  ? "bg-brand-500 border-brand-500 text-white"
                  : "border-slate-700 text-slate-400 hover:border-slate-500"
              }`}
            >
              {s.replace("_", " ")}
            </button>
          ))}
        </div>

        {/* Tailor button */}
        {!app.tailored_cv_text && (
          <button
            onClick={handleTailor}
            disabled={tailoring}
            className="w-full py-3 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 transition-colors mb-6"
          >
            {tailoring ? "Tailoring…" : "⚡ Generate tailored CV + Cover Letter"}
          </button>
        )}

        {/* Streaming log */}
        {tailorLog.length > 0 && (
          <div className="mb-6 p-4 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs text-slate-400 space-y-1">
            {tailorLog.map((line, i) => <div key={i}>{line}</div>)}
          </div>
        )}

        {/* Tailored docs */}
        {app.tailored_cv_text && (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800">
              <h3 className="font-semibold mb-3">Tailored CV</h3>
              <pre className="text-slate-400 text-sm whitespace-pre-wrap leading-relaxed">{app.tailored_cv_text}</pre>
            </div>
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800">
              <h3 className="font-semibold mb-3">Cover Letter</h3>
              <pre className="text-slate-400 text-sm whitespace-pre-wrap leading-relaxed">{app.cover_letter_text}</pre>
            </div>
          </div>
        )}

        {/* Interview prep */}
        {app.status === "interviewing" && (
          <Link
            href={`/applications/${id}/prep`}
            className="block mt-6 text-center py-3 font-semibold rounded-xl border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white transition-colors"
          >
            🎯 Generate Interview Prep →
          </Link>
        )}
      </div>
    </main>
  );
}
