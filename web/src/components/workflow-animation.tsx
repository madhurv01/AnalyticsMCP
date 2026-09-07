"use client";

import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { WORKFLOW_STEPS, stepIndex } from "@/lib/workflow";
import type { Job } from "@/lib/api";

export function WorkflowAnimation({ job }: { job: Job }) {
  const active = stepIndex(job.step);
  const done = job.status === "succeeded";
  const failed = job.status === "failed";

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Analysis workflow</h3>
        <span className="text-sm muted">{job.progress}%</span>
      </div>

      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
        <motion.div
          className="h-full rounded-full bg-brand"
          animate={{ width: `${done ? 100 : job.progress}%` }}
          transition={{ ease: "easeOut", duration: 0.5 }}
        />
      </div>

      <ul className="mt-5 grid gap-2 sm:grid-cols-2">
        {WORKFLOW_STEPS.map((s, i) => {
          const state =
            done || i < active ? "done" : i === active && !failed ? "active" : "pending";
          return (
            <motion.li
              key={s.key}
              className="flex items-center gap-3 rounded-lg border p-2.5 text-sm"
              style={{ borderColor: "var(--border)" }}
              animate={{
                opacity: state === "pending" ? 0.5 : 1,
                scale: state === "active" ? 1.01 : 1,
              }}
            >
              <span
                className={`grid h-6 w-6 place-items-center rounded-full text-white ${
                  state === "done"
                    ? "bg-emerald-500"
                    : state === "active"
                      ? "bg-brand"
                      : "bg-slate-300 dark:bg-slate-700"
                }`}
              >
                {state === "done" ? (
                  <Check size={13} />
                ) : state === "active" ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <span className="text-[10px]">{i + 1}</span>
                )}
              </span>
              {s.label}
            </motion.li>
          );
        })}
      </ul>

      {failed && (
        <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
          {job.error ?? "Analysis failed."}
        </p>
      )}
    </div>
  );
}
