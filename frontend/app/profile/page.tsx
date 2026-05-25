"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import Navbar from "@/components/Navbar";

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getProfile().then(setProfile).catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    await api.updatePreferences({
      target_roles: profile.target_roles,
      target_locations: profile.target_locations,
      salary_min: profile.salary_min,
      salary_max: profile.salary_max,
      experience_level: profile.experience_level,
    });
    setSaving(false);
  }

  if (!profile) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-500">Loading profile…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950">
      <Navbar />
      <div className="max-w-2xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold mb-8">Your Profile</h1>

        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Target roles</label>
            <input
              type="text"
              value={profile.target_roles?.join(", ") ?? ""}
              onChange={(e) => setProfile({ ...profile, target_roles: e.target.value.split(",").map((s: string) => s.trim()) })}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Target locations</label>
            <input
              type="text"
              value={profile.target_locations?.join(", ") ?? ""}
              onChange={(e) => setProfile({ ...profile, target_locations: e.target.value.split(",").map((s: string) => s.trim()) })}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Min salary (£)</label>
              <input type="number" value={profile.salary_min ?? ""} onChange={(e) => setProfile({ ...profile, salary_min: parseInt(e.target.value) })}
                className="w-full px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Max salary (£)</label>
              <input type="number" value={profile.salary_max ?? ""} onChange={(e) => setProfile({ ...profile, salary_max: parseInt(e.target.value) })}
                className="w-full px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500" />
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-8 py-2.5 font-semibold rounded-lg bg-brand-500 hover:bg-brand-600 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving…" : "Save preferences"}
          </button>
        </div>

        {/* CV structured data */}
        {profile.cv_structured && (
          <div className="mt-10">
            <h2 className="text-lg font-semibold mb-4">Parsed CV Data</h2>
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
              <pre className="text-xs text-slate-400 whitespace-pre-wrap">
                {JSON.stringify(profile.cv_structured, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
