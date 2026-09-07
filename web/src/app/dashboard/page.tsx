"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, FileSpreadsheet, Trash2, Play } from "lucide-react";
import { api, type Dataset, type Job, type Report, type User } from "@/lib/api";
import { TopBar } from "@/components/top-bar";
import { UploadDropzone } from "@/components/upload-dropzone";
import { WorkflowAnimation } from "@/components/workflow-animation";
import { InsightsPanel } from "@/components/insights-panel";
import { bytes } from "@/lib/utils";

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const poll = useRef<ReturnType<typeof setInterval>>();

  const refresh = useCallback(async () => {
    const [d, r] = await Promise.all([api.datasets(), api.reports()]);
    setDatasets(d.items);
    setReports(r.items);
  }, []);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => (location.href = "/"));
    refresh();
    return () => clearInterval(poll.current);
  }, [refresh]);

  function watch(id: string) {
    clearInterval(poll.current);
    poll.current = setInterval(async () => {
      try {
        const j = await api.job(id);
        setJob(j);
        if (j.status === "succeeded" || j.status === "failed") {
          clearInterval(poll.current);
          refresh();
        }
      } catch {
        clearInterval(poll.current);
      }
    }, 900);
  }

  async function onFile(f: File) {
    setError(null);
    setBusy(true);
    try {
      const ds = await api.upload(f);
      await refresh();
      const j = await api.analyze(ds.id);
      setJob(j);
      if (j.status !== "succeeded") watch(j.id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runAnalysis(id: string) {
    setError(null);
    try {
      const j = await api.analyze(id);
      setJob(j);
      if (j.status !== "succeeded") watch(j.id);
      else refresh();
    } catch (e: any) {
      setError(e.message);
    }
  }

  const reportForJob = job && reports.find((r) => r.job_id === job.id);

  return (
    <div className="min-h-screen">
      <TopBar user={user} />
      <main className="mx-auto grid max-w-6xl gap-6 px-5 py-8 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <UploadDropzone onFile={onFile} busy={busy} />

          {error && (
            <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40">
              {error}
            </p>
          )}

          <AnimatePresence mode="wait">
            {job && (
              <motion.div
                key={job.id + job.status}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                {job.status !== "succeeded" ? (
                  <WorkflowAnimation job={job} />
                ) : (
                  <>
                    {reportForJob && (
                      <div className="card flex items-center justify-between p-5">
                        <div className="flex items-center gap-3">
                          <FileSpreadsheet className="text-emerald-500" />
                          <div>
                            <p className="font-medium">Excel report ready</p>
                            <p className="text-sm muted">
                              {reportForJob.sheet_names.length} sheets ·{" "}
                              {bytes(reportForJob.size_bytes)}
                            </p>
                          </div>
                        </div>
                        <a
                          className="btn-primary"
                          href={api.downloadUrl(reportForJob.id)}
                        >
                          <Download size={16} /> Download
                        </a>
                      </div>
                    )}
                    <InsightsPanel job={job} />
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <aside className="space-y-6">
          <section className="card p-4">
            <h3 className="mb-3 text-sm font-semibold">Datasets</h3>
            <ul className="space-y-2">
              {datasets.length === 0 && (
                <li className="text-sm muted">No uploads yet.</li>
              )}
              {datasets.map((d) => (
                <li
                  key={d.id}
                  className="flex items-center justify-between gap-2 rounded-lg border p-2.5 text-sm"
                  style={{ borderColor: "var(--border)" }}
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{d.filename}</p>
                    <p className="muted">
                      {bytes(d.size_bytes)}
                      {d.row_count ? ` · ${d.row_count.toLocaleString()} rows` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <button
                      className="btn-ghost !p-1.5"
                      onClick={() => runAnalysis(d.id)}
                      title="Analyze"
                    >
                      <Play size={14} />
                    </button>
                    <button
                      className="btn-ghost !p-1.5"
                      onClick={async () => {
                        await api.deleteDataset(d.id);
                        refresh();
                      }}
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="card p-4">
            <h3 className="mb-3 text-sm font-semibold">Report history</h3>
            <ul className="space-y-2">
              {reports.length === 0 && (
                <li className="text-sm muted">No reports yet.</li>
              )}
              {reports.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between gap-2 rounded-lg border p-2.5 text-sm"
                  style={{ borderColor: "var(--border)" }}
                >
                  <span className="muted">
                    {new Date(r.created_at).toLocaleString()}
                  </span>
                  <a
                    className="btn-ghost !p-1.5"
                    href={api.downloadUrl(r.id)}
                    title="Download"
                  >
                    <Download size={14} />
                  </a>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </main>
    </div>
  );
}
