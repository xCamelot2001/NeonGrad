import { createClient } from "@/lib/supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Auth helpers ──────────────────────────────────────────────────────────────

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error("Not authenticated. Please sign in.");
  return {
    Authorization: `Bearer ${session.access_token}`,
    "Content-Type": "application/json",
  };
}

async function getToken(): Promise<string> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error("Not authenticated.");
  return session.access_token;
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

// ── CV upload (multipart) ─────────────────────────────────────────────────────

export async function apiUploadCV(file: File) {
  const token = await getToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/profile/cv`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ── Tailoring SSE stream ──────────────────────────────────────────────────────
//
// EventSource doesn't support custom headers, so we use fetch() + ReadableStream
// to stream the SSE events while still sending the Bearer token.
//
// Usage:
//   const stop = api.streamTailoring(appId, (evt) => {
//     if (evt.type === "log")  addLog(evt.message);
//     if (evt.type === "done") setDone(true);
//   });
//   // call stop() to abort early

export function streamTailoring(
  applicationId: string,
  onEvent: (evt: { type: string; message?: string }) => void,
): () => void {
  const controller = new AbortController();

  (async () => {
    const token = await getToken();
    const res = await fetch(
      `${API_URL}/api/applications/${applicationId}/tailor`,
      {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      },
    );

    if (!res.ok || !res.body) {
      onEvent({ type: "error", message: `HTTP ${res.status}` });
      return;
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE lines end with \n\n; process all complete events in the buffer
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? ""; // keep any incomplete tail

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        try {
          const evt = JSON.parse(line.slice(5).trim());
          onEvent(evt);
          if (evt.type === "done" || evt.type === "error") return;
        } catch { /* malformed line — skip */ }
      }
    }
  })().catch((err) => {
    if (err?.name !== "AbortError") {
      onEvent({ type: "error", message: String(err) });
    }
  });

  return () => controller.abort();
}

// ── PDF download ──────────────────────────────────────────────────────────────

export async function downloadPdf(
  applicationId: string,
  docType: "cv" | "cover_letter",
  filename: string,
): Promise<void> {
  const token = await getToken();
  const res   = await fetch(
    `${API_URL}/api/applications/${applicationId}/download/${docType}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(`Download failed: ${res.status}`);

  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── REST API surface ──────────────────────────────────────────────────────────

export const api = {
  // Profile
  getProfile:        () => apiFetch("/api/profile"),
  updatePreferences: (data: object) =>
    apiFetch("/api/profile/preferences", { method: "PUT", body: JSON.stringify(data) }),

  // Jobs
  getRankedJobs: (limit?: number) =>
    apiFetch(`/api/jobs/ranked${limit ? `?limit=${limit}` : ""}`),
  getJob:        (id: string) => apiFetch(`/api/jobs/${id}`),
  discoverJobs:  () => apiFetch("/api/jobs/discover", { method: "POST" }),
  rankJobs:      () => apiFetch("/api/jobs/rank",    { method: "POST" }),

  // Applications
  getApplications:  () => apiFetch("/api/applications"),
  getApplication:   (id: string) => apiFetch(`/api/applications/${id}`),
  createApplication:(jobId: string) =>
    apiFetch("/api/applications", { method: "POST", body: JSON.stringify({ job_id: jobId }) }),
  updateStatus: (id: string, status: string) =>
    apiFetch(`/api/applications/${id}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),
};
