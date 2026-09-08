"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Download,
  Play,
  Trash2,
  Database,
  FileSpreadsheet,
  GitCompareArrows,
  Activity,
} from "lucide-react";
import { api, type Dataset, type Job, type Report } from "@/lib/api";
import { bytes } from "@/lib/utils";
import { QualityGauge } from "./quality-gauge";

const sevDot: Record<string, string> = {
  critical: "bg-rose-500",
  warning: "bg-amber-500",
  info: "bg-emerald-500",
};

function DriftCard({ drift }: { drift: any }) {
  if (!drift) return null;
  const dot = sevDot[drift.severity] ?? "bg-slate-400";
  return (
    <div className="card-2 p-4">
      <h4 className="flex items-center gap-2 text-sm font-semibold">
        <GitCompareArrows size={15} className="text-brand" /> Schema drift
      </h4>
      <div className="mt-2 flex items-start gap-2 text-xs">
        <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${dot} animate-pulse-glow`} />
        <p className="muted">{drift.summary}</p>
      </div>
      {drift.status === "compared" && (
        <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
          {drift.added?.map((c: string) => (
            <span key={c} className="chip !bg-emerald-500/15 !text-emerald-500">+ {c}</span>
          ))}
          {drift.removed?.map((c: string) => (
            <span key={c} className="chip !bg-rose-500/15 !text-rose-500">− {c}</span>
          ))}
          {drift.role_changes?.map((r: any) => (
            <span key={r.column} className="chip !bg-amber-500/15 !text-amber-500">
              {r.column}: {r.from}→{r.to}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function AnalysisSnapshot({ job }: { job: Job }) {
  const ins = job.insights_json ?? {};
  const profile = job.profile_json ?? {};
  const quality = ins.quality;

  return (
    <div className="card p-5">
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <Activity size={15} className="text-brand" /> Analysis snapshot
      </h3>

      {quality && (
        <div className="mt-4 flex flex-col items-center">
          <QualityGauge score={quality.overall} grade={quality.grade} />
          <div className="mt-4 w-full space-y-1.5">
            {quality.subscores.map((s: any) => (
              <div key={s.key} className="flex items-center gap-2 text-xs">
                <span className="w-28 shrink-0 muted">{s.label}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                    initial={{ width: 0 }}
                    animate={{ width: `${s.score}%` }}
                    transition={{ duration: 0.7 }}
                  />
                </div>
                <span className="w-8 shrink-0 text-right">{Math.round(s.score)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 grid grid-cols-2 gap-2">
        {[
          ["Rows", profile.row_count?.toLocaleString() ?? "—"],
          ["Columns", profile.col_count ?? "—"],
          ["Missing", `${profile.missing_cell_pct ?? 0}%`],
          ["Duplicates", profile.duplicate_rows ?? 0],
        ].map(([k, v]) => (
          <div key={k as string} className="card-2 px-3 py-2">
            <p className="text-[11px] muted">{k}</p>
            <p className="text-lg font-semibold text-brand">{v}</p>
          </div>
        ))}
      </div>

      <div className="mt-3">
        <DriftCard drift={ins.drift} />
      </div>
    </div>
  );
}

export function RightRail({
  job,
  datasets,
  reports,
  onAnalyze,
  onRefresh,
}: {
  job: Job | null;
  datasets: Dataset[];
  reports: Report[];
  onAnalyze: (id: string) => void;
  onRefresh: () => void;
}) {
  const [tab, setTab] = useState<"datasets" | "reports">("datasets");
  const showSnapshot = job?.status === "succeeded";

  return (
    <aside className="space-y-5 lg:sticky lg:top-[76px] lg:max-h-[calc(100vh-96px)] lg:overflow-y-auto lg:pr-1 scroll-thin">
      <AnimatePresence mode="wait">
        {showSnapshot && (
          <motion.div
            key="snap"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <AnalysisSnapshot job={job!} />
          </motion.div>
        )}
      </AnimatePresence>

      <section className="card p-4">
        <div className="mb-3 flex gap-1 rounded-xl bg-black/5 p-1 text-sm dark:bg-white/5">
          {(["datasets", "reports"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 rounded-lg px-3 py-1.5 font-medium capitalize transition ${
                tab === t
                  ? "bg-[var(--card)] shadow-glow-sm text-brand"
                  : "muted"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "datasets" ? (
          <ul className="space-y-2">
            {datasets.length === 0 && <li className="text-sm muted">No uploads yet.</li>}
            {datasets.map((d) => (
              <li
                key={d.id}
                className="flex items-center justify-between gap-2 rounded-lg border p-2.5 text-sm"
                style={{ borderColor: "var(--border)" }}
              >
                <div className="flex min-w-0 items-center gap-2">
                  <Database size={14} className="shrink-0 muted" />
                  <div className="min-w-0">
                    <p className="truncate font-medium">{d.filename}</p>
                    <p className="text-xs muted">
                      {bytes(d.size_bytes)}
                      {d.row_count ? ` · ${d.row_count.toLocaleString()} rows` : ""}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button className="btn-ghost !p-1.5" onClick={() => onAnalyze(d.id)} title="Analyze">
                    <Play size={13} />
                  </button>
                  <button
                    className="btn-ghost !p-1.5"
                    onClick={async () => {
                      await api.deleteDataset(d.id);
                      onRefresh();
                    }}
                    title="Delete"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <ul className="space-y-2">
            {reports.length === 0 && <li className="text-sm muted">No reports yet.</li>}
            {reports.map((r) => (
              <li
                key={r.id}
                className="flex items-center justify-between gap-2 rounded-lg border p-2.5 text-sm"
                style={{ borderColor: "var(--border)" }}
              >
                <div className="flex min-w-0 items-center gap-2">
                  <FileSpreadsheet size={14} className="shrink-0 text-emerald-500" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium">
                      {r.sheet_names.length} sheets · {bytes(r.size_bytes)}
                    </p>
                    <p className="text-xs muted">
                      {new Date(r.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <a
                  className="btn-ghost !p-1.5"
                  href={api.downloadUrl(r.id)}
                  title="Download"
                >
                  <Download size={13} />
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
