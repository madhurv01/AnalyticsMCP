export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface User {
  id: string;
  email: string;
  name: string | null;
  picture_url: string | null;
}

export interface Dataset {
  id: string;
  filename: string;
  size_bytes: number;
  row_count: number | null;
  col_count: number | null;
  status: string;
  created_at: string;
}

export interface Job {
  id: string;
  dataset_id: string;
  mode: string;
  status: "queued" | "running" | "succeeded" | "failed";
  step: string | null;
  progress: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  profile_json?: any;
  insights_json?: any;
}

export interface Report {
  id: string;
  job_id: string;
  size_bytes: number;
  sheet_names: string[];
  created_at: string;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
  });
  if (res.status === 401) throw new Error("unauthorized");
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  loginUrl: () => `${API_BASE}/api/auth/google/login`,
  me: () => req<User>("/api/auth/me"),
  logout: () => req("/api/auth/logout", { method: "POST" }),

  datasets: (limit = 20, offset = 0) =>
    req<{ items: Dataset[]; total: number }>(
      `/api/datasets?limit=${limit}&offset=${offset}`,
    ),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<Dataset>("/api/datasets", { method: "POST", body: fd });
  },
  deleteDataset: (id: string) =>
    req(`/api/datasets/${id}`, { method: "DELETE" }),
  analyze: (id: string, force_async = false) =>
    req<Job>(`/api/datasets/${id}/analyze`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ force_async }),
    }),

  job: (id: string) => req<Job>(`/api/jobs/${id}`),
  jobs: (limit = 20) =>
    req<{ items: Job[]; total: number }>(`/api/jobs?limit=${limit}`),

  reports: (limit = 20) =>
    req<{ items: Report[]; total: number }>(`/api/reports?limit=${limit}`),
  downloadUrl: (reportId: string) =>
    `${API_BASE}/api/reports/${reportId}/download`,
  deleteReport: (id: string) =>
    req(`/api/reports/${id}`, { method: "DELETE" }),
};
