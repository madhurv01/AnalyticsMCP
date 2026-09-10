"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, FileSpreadsheet } from "lucide-react";
import { api, type Dataset, type Job, type Report, type User } from "@/lib/api";
import { TopBar } from "@/components/top-bar";
import { UploadDropzone } from "@/components/upload-dropzone";
import { WorkflowAnimation } from "@/components/workflow-animation";
import { InsightsPanel } from "@/components/insights-panel";
import { DriverPanel } from "@/components/driver-panel";
import { RightRail } from "@/components/right-rail";
import { DataSources } from "@/components/data-sources";
import { QueryConsole } from "@/components/query-console";
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

  async function track(j: Job) {
    if (j.status === "succeeded" || j.status === "failed") {
      // inline jobs come back done — fetch the full detail (profile + insights)
      setJob(await api.job(j.id));
      refresh();
    } else {
      setJob(j);
      watch(j.id);
    }
  }

  async function onFile(f: File) {
    setError(null);
    setBusy(true);
    try {
      const ds = await api.upload(f);
      await refresh();
      await track(await api.analyze(ds.id));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runAnalysis(id: string) {
    setError(null);
    try {
      await track(await api.analyze(id));
    } catch (e: any) {
      setError(e.message);
    }
  }

  const reportForJob = job && reports.find((r) => r.job_id === job.id);
  const drivers = job?.insights_json?.drivers;

  return (
    <div className="min-h-screen">
      <TopBar user={user} />
      <main className="mx-auto grid max-w-7xl gap-6 px-5 py-8 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <UploadDropzone onFile={onFile} busy={busy} />

          <DataSources
            onImported={async (id) => {
              setError(null);
              await refresh();
              try {
                await track(await api.analyze(id));
              } catch (e: any) {
                setError(e.message);
              }
            }}
          />

          {error && (
            <p className="rounded-xl bg-rose-500/10 p-3 text-sm text-rose-500">{error}</p>
          )}

          {!job && (
            <div className="card p-8 text-center">
              <p className="text-sm muted">
                Upload a CSV to start — or pick one from your history on the right.
              </p>
            </div>
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
                      <div className="card glow-ring flex items-center justify-between p-5">
                        <div className="flex items-center gap-3">
                          <span className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-500/15 text-emerald-500">
                            <FileSpreadsheet size={20} />
                          </span>
                          <div>
                            <p className="font-medium">Excel report ready</p>
                            <p className="text-sm muted">
                              {reportForJob.sheet_names.length} sheets ·{" "}
                              {bytes(reportForJob.size_bytes)}
                            </p>
                          </div>
                        </div>
                        <a className="btn-primary" href={api.downloadUrl(reportForJob.id)}>
                          <Download size={16} /> Download
                        </a>
                      </div>
                    )}
                    <InsightsPanel job={job} />
                    {drivers && <DriverPanel drivers={drivers} />}
                    <QueryConsole datasetId={job.dataset_id} />
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <RightRail
          job={job}
          datasets={datasets}
          reports={reports}
          onAnalyze={runAnalysis}
          onRefresh={refresh}
        />
      </main>
    </div>
  );
}
