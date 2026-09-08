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
  critical: "text-rose-500 bg-rose-500/10",
  warning: "text-amber-500 bg-amber-500/10",
  info: "text-slate-500 bg-slate-500/10 dark:text-slate-300",
};

export function InsightsPanel({ job }: { job: Job }) {
  const ins = job.insights_json;
  if (!ins) return null;

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <p className="text-xs font-semibold uppercase tracking-wide muted">Headline</p>
        <p className="mt-1.5 text-sm leading-relaxed">{ins.headline}</p>
        {ins.counts && (
          <div className="mt-3 flex gap-2 text-xs">
            {ins.counts.critical > 0 && (
              <span className="chip !bg-rose-500/15 !text-rose-500">
                {ins.counts.critical} critical
              </span>
            )}
            {ins.counts.warning > 0 && (
              <span className="chip !bg-amber-500/15 !text-amber-500">
                {ins.counts.warning} warning
              </span>
            )}
            <span className="chip">{ins.counts.info} info</span>
          </div>
        )}
      </div>

      <div className="card p-5">
        <h3 className="font-semibold">Findings</h3>
        <ul className="mt-3 space-y-2">
          {ins.findings?.map((f: any, i: number) => {
            const Icon = sevIcon[f.severity] ?? Info;
            return (
              <motion.li
                key={i}
                className={`flex gap-3 rounded-xl p-3 text-sm ${sevColor[f.severity]}`}
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
                className="rounded-xl border p-3 text-sm"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="rounded bg-brand-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-brand-500">
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
