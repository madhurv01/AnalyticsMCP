"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Info, Lightbulb, TriangleAlert } from "lucide-react";
import type { Job } from "@/lib/api";

const sevIcon: Record<string, any> = {
  critical: TriangleAlert,
  warning: AlertTriangle,
  info: Info,
};
const sevColor: Record<string, string> = {
  critical: "text-red-600 bg-red-50 dark:bg-red-950/40",
  warning: "text-amber-600 bg-amber-50 dark:bg-amber-950/40",
  info: "text-slate-500 bg-slate-50 dark:bg-slate-800/40",
};

export function InsightsPanel({ job }: { job: Job }) {
  const ins = job.insights_json;
  const profile = job.profile_json;
  if (!ins) return null;

  const kpis = [
    ["Rows", profile?.row_count?.toLocaleString()],
    ["Columns", profile?.col_count],
    ["Missing", `${profile?.missing_cell_pct ?? 0}%`],
    ["Duplicates", profile?.duplicate_rows ?? 0],
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {kpis.map(([label, val], i) => (
          <motion.div
            key={label as string}
            className="card p-4"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <p className="text-xs muted">{label}</p>
            <p className="mt-1 text-2xl font-bold text-brand">{val ?? "—"}</p>
          </motion.div>
        ))}
      </div>

      <div className="card p-5">
        <p className="text-sm">{ins.headline}</p>
      </div>

      <div className="card p-5">
        <h3 className="font-semibold">Findings</h3>
        <ul className="mt-3 space-y-2">
          {ins.findings?.map((f: any, i: number) => {
            const Icon = sevIcon[f.severity] ?? Info;
            return (
              <motion.li
                key={i}
                className={`flex gap-3 rounded-lg p-3 text-sm ${sevColor[f.severity]}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <Icon size={16} className="mt-0.5 shrink-0" />
                <span>
                  <span className="font-medium">{f.title}</span>
                  <span className="muted"> — {f.evidence}</span>
                </span>
              </motion.li>
            );
          })}
        </ul>
      </div>

      {ins.recommendations?.length > 0 && (
        <div className="card p-5">
          <h3 className="flex items-center gap-2 font-semibold">
            <Lightbulb size={16} className="text-brand" /> Recommendations
          </h3>
          <ul className="mt-3 space-y-2">
            {ins.recommendations.map((r: any, i: number) => (
              <li
                key={i}
                className="rounded-lg border p-3 text-sm"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="rounded bg-brand-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-brand-700">
                  {r.priority}
                </span>
                <span className="ml-2 font-medium">{r.title}</span>
                <p className="mt-1 muted">{r.detail}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
