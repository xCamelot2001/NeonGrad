import { createClient } from "@/lib/supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error("Not authenticated. Please sign in.");
  return {
    "Authorization": `Bearer ${session.access_token}`,
    "Content-Type": "application/json",
  };
}

async function apiFetch(path: string, options?: RequestInit) {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...authHeaders, ...(options?.headers ?? {}) },
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error);
  }
  return res.json();
}

export async function apiUploadCV(file: File) {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error("Not authenticated.");

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/profile/cv`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${session.access_token}` },
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  // Profile
  getProfile: () => apiFetch("/api/profile"),
  updatePreferences: (data: object) =>
    apiFetch("/api/profile/preferences", { method: "PUT", body: JSON.stringify(data) }),

  // Jobs
  getRankedJobs: (limit?: number) => apiFetch(`/api/jobs/ranked${limit ? `?limit=${limit}` : ""}`),
  getJob: (id: string) => apiFetch(`/api/jobs/${id}`),
  discoverJobs: () => apiFetch("/api/jobs/discover", { method: "POST" }),
  rankJobs: () => apiFetch("/api/jobs/rank", { method: "POST" }),

  // Applications
  getApplications: () => apiFetch("/api/applications"),
  getApplication: (id: string) => apiFetch(`/api/applications/${id}`),
  createApplication: (jobId: string) =>
    apiFetch("/api/applications", { method: "POST", body: JSON.stringify({ job_id: jobId }) }),
  updateStatus: (id: string, status: string) =>
    apiFetch(`/api/applications/${id}/status`, { method: "PUT", body: JSON.stringify({ status }) }),
};
