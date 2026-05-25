"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiUploadCV, api } from "@/lib/api";

const STEPS = ["Upload CV", "Your Preferences", "First Discovery"];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [parsed, setParsed] = useState(false);
  const [prefs, setPrefs] = useState({
    targetRoles: "",
    targetLocations: "",
    salaryMin: "",
    salaryMax: "",
    experienceLevel: "mid",
  });
  const [discovering, setDiscovering] = useState(false);

  // Guard: redirect users who already completed onboarding
  useEffect(() => {
    api.getProfile()
      .then((profile) => {
        const hasPrefs = Array.isArray(profile?.target_roles) && profile.target_roles.length > 0;
        if (hasPrefs) router.push("/dashboard");
      })
      .catch(() => { /* not logged in or network error — let onboarding render */ });
  }, []);

  // ── Step 1: CV Upload ──────────────────────────────────────────────────────
  async function handleCvUpload() {
    if (!cvFile) return;
    setUploading(true);
    try {
      await apiUploadCV(cvFile);
      setParsed(true);
      setTimeout(() => setStep(1), 800);
    } catch (e) {
      alert(`CV upload failed: ${e}`);
    } finally {
      setUploading(false);
    }
  }

  // ── Step 2: Save preferences ───────────────────────────────────────────────
  async function handlePrefs() {
    const payload = {
      target_roles: prefs.targetRoles.split(",").map((s) => s.trim()).filter(Boolean),
      target_locations: prefs.targetLocations.split(",").map((s) => s.trim()).filter(Boolean),
      salary_min: prefs.salaryMin ? parseInt(prefs.salaryMin) : null,
      salary_max: prefs.salaryMax ? parseInt(prefs.salaryMax) : null,
      experience_level: prefs.experienceLevel,
    };
    await api.updatePreferences(payload);
    setStep(2);
  }

  // ── Step 3: First discovery ────────────────────────────────────────────────
  async function handleDiscover() {
    setDiscovering(true);
    await api.discoverJobs();
    setDiscovering(false);
    router.push("/dashboard");
  }

  return (
    <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center px-4">
      {/* Progress bar */}
      <div className="w-full max-w-lg mb-8">
        <div className="flex items-center gap-2 mb-4">
          {STEPS.map((s, i) => (
            <div key={s} className="flex-1 flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold mb-1 transition-colors ${
                  i < step
                    ? "bg-brand-500 text-white"
                    : i === step
                    ? "border-2 border-brand-500 text-brand-500"
                    : "border-2 border-slate-700 text-slate-600"
                }`}
              >
                {i < step ? "✓" : i + 1}
              </div>
              <span className={`text-xs ${i === step ? "text-brand-500" : "text-slate-600"}`}>
                {s}
              </span>
            </div>
          ))}
        </div>
        <div className="h-1 bg-slate-800 rounded-full">
          <div
            className="h-1 bg-brand-500 rounded-full transition-all duration-500"
            style={{ width: `${(step / (STEPS.length - 1)) * 100}%` }}
          />
        </div>
      </div>

      {/* Step panels */}
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-8">
        {step === 0 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold">Upload your CV</h2>
            <p className="text-slate-400 text-sm">
              We'll extract your skills, experience, and education automatically using AI.
            </p>
            <label className="block border-2 border-dashed border-slate-700 hover:border-brand-500 rounded-xl p-8 text-center cursor-pointer transition-colors">
              <input
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                onChange={(e) => setCvFile(e.target.files?.[0] ?? null)}
              />
              {cvFile ? (
                <span className="text-brand-400 font-medium">{cvFile.name}</span>
              ) : (
                <>
                  <div className="text-4xl mb-2">📄</div>
                  <p className="text-slate-400">Click to upload PDF or DOCX</p>
                </>
              )}
            </label>
            {parsed && <p className="text-green-400 text-sm">✓ CV parsed successfully!</p>}
            <button
              onClick={handleCvUpload}
              disabled={!cvFile || uploading}
              className="w-full py-3 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 transition-colors"
            >
              {uploading ? "Parsing with AI…" : "Upload & Parse"}
            </button>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <h2 className="text-2xl font-bold">Your job preferences</h2>
            <p className="text-slate-400 text-sm">
              Tell NeonGrad what you're looking for. Separate multiple values with commas.
            </p>
            {[
              { label: "Target roles", key: "targetRoles", placeholder: "ML Engineer, AI Engineer, Data Scientist" },
              { label: "Target locations", key: "targetLocations", placeholder: "London, Remote, Berlin" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-slate-300 mb-1">{label}</label>
                <input
                  type="text"
                  value={prefs[key as keyof typeof prefs]}
                  onChange={(e) => setPrefs({ ...prefs, [key]: e.target.value })}
                  placeholder={placeholder}
                  className="w-full px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
                />
              </div>
            ))}
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: "Min salary (£)", key: "salaryMin", placeholder: "40000" },
                { label: "Max salary (£)", key: "salaryMax", placeholder: "80000" },
              ].map(({ label, key, placeholder }) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-slate-300 mb-1">{label}</label>
                  <input
                    type="number"
                    value={prefs[key as keyof typeof prefs]}
                    onChange={(e) => setPrefs({ ...prefs, [key]: e.target.value })}
                    placeholder={placeholder}
                    className="w-full px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
                  />
                </div>
              ))}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Experience level</label>
              <select
                value={prefs.experienceLevel}
                onChange={(e) => setPrefs({ ...prefs, experienceLevel: e.target.value })}
                className="w-full px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
              >
                <option value="junior">Junior (0–2 years)</option>
                <option value="mid">Mid (2–5 years)</option>
                <option value="senior">Senior (5+ years)</option>
              </select>
            </div>
            <button
              onClick={handlePrefs}
              className="w-full py-3 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 transition-colors"
            >
              Save preferences
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6 text-center">
            <div className="text-6xl">🚀</div>
            <h2 className="text-2xl font-bold">Ready to launch</h2>
            <p className="text-slate-400">
              NeonGrad will now search for jobs matching your profile across Adzuna and rank
              them by AI-assessed fit. This takes about 30 seconds.
            </p>
            <button
              onClick={handleDiscover}
              disabled={discovering}
              className="w-full py-3 font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 transition-colors"
            >
              {discovering ? "Finding your jobs…" : "Run first job discovery →"}
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
