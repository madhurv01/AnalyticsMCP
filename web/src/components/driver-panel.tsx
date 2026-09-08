"use client";

import { motion } from "framer-motion";
import { GitBranch, Target, TrendingUp, TrendingDown } from "lucide-react";

export function DriverPanel({ drivers }: { drivers: any }) {
  const targets: any[] = drivers?.targets ?? [];
  if (targets.length === 0) {
    return (
      <div className="card p-5">
        <h3 className="flex items-center gap-2 font-semibold">
          <Target size={16} className="text-brand" /> Driver analysis
        </h3>
        <p className="mt-2 text-sm muted">
          {drivers?.note ?? "No suitable target column was found in this dataset."}
        </p>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <h3 className="flex items-center gap-2 font-semibold">
        <Target size={16} className="text-brand" /> Driver analysis
      </h3>
      <p className="mt-1 text-sm muted">
        What moves the key metrics, from a shallow decision tree + segment lift.
      </p>

      <div className="mt-4 space-y-6">
        {targets.map((t, ti) => {
          const maxImp = Math.max(...t.drivers.map((d: any) => d.importance), 0.0001);
          return (
            <motion.div
              key={t.target}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: ti * 0.1 }}
              className="card-2 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">
                  Target: <span className="text-brand">{t.target}</span>
                </span>
                <span className="chip">
                  {t.fit_metric.name} {t.fit_metric.value}
                </span>
              </div>

              <p className="mt-3 text-xs font-semibold uppercase tracking-wide muted">
                Top drivers
              </p>
              <div className="mt-2 space-y-1.5">
                {t.drivers.map((d: any) => (
                  <div key={d.feature} className="flex items-center gap-2 text-sm">
                    <span className="w-40 shrink-0 truncate" title={d.feature}>
                      {d.feature}
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                        initial={{ width: 0 }}
                        animate={{ width: `${(d.importance / maxImp) * 100}%` }}
                        transition={{ duration: 0.6 }}
                      />
                    </div>
                    <span className="w-12 shrink-0 text-right text-xs muted">
                      {(d.importance * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>

              {t.rules?.length > 0 && (
                <>
                  <p className="mt-4 text-xs font-semibold uppercase tracking-wide muted">
                    Decision rules
                  </p>
                  <ul className="mt-2 space-y-1.5">
                    {t.rules.map((r: any, i: number) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 rounded-lg border p-2 text-xs"
                        style={{ borderColor: "var(--border)" }}
                      >
                        <GitBranch size={13} className="mt-0.5 shrink-0 text-brand" />
                        <span>
                          <code className="text-[11px]">{r.condition}</code>
                          <span className="muted">
                            {" → "}
                            {t.target_kind === "numeric"
                              ? `mean ${r.mean}`
                              : `${r.outcome} (${Math.round(r.confidence * 100)}%)`}{" "}
                            · n={r.support}
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {t.segments?.length > 0 && (
                <>
                  <p className="mt-4 text-xs font-semibold uppercase tracking-wide muted">
                    Standout segments
                  </p>
                  <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
                    {t.segments.slice(0, 6).map((s: any, i: number) => {
                      const up = (s.lift_pct ?? 0) >= 0;
                      return (
                        <div
                          key={i}
                          className="flex items-center justify-between rounded-lg border p-2 text-xs"
                          style={{ borderColor: "var(--border)" }}
                        >
                          <span className="truncate" title={`${s.column} = ${s.value}`}>
                            {s.column} = <b>{s.value}</b>
                          </span>
                          <span
                            className={`flex shrink-0 items-center gap-0.5 font-medium ${
                              up ? "text-emerald-500" : "text-rose-500"
                            }`}
                          >
                            {up ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                            {s.lift_pct > 0 ? "+" : ""}
                            {s.lift_pct}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
