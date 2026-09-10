"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Terminal, Play, Loader2 } from "lucide-react";
import { api, type QueryResult } from "@/lib/api";

const EXAMPLES = [
  "df.describe()",
  "df.groupby('region')['revenue_usd'].mean().sort_values(ascending=False)",
  "df[df['units'] > 5]['segment'].value_counts()",
];

function ResultView({ r }: { r: QueryResult }) {
  if (r.error) return <p className="text-sm text-rose-500">{r.error}</p>;

  if (r.kind === "table") {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left muted">
              {r.columns?.map((c) => (
                <th key={c} className="whitespace-nowrap px-2 py-1">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {r.rows?.slice(0, 50).map((row, i) => (
              <tr key={i} className="border-t" style={{ borderColor: "var(--border)" }}>
                {r.columns?.map((c) => (
                  <td key={c} className="whitespace-nowrap px-2 py-1">{String(row[c] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-1 text-[11px] muted">
          {r.row_count} rows{r.result_truncated ? ` (showing ${r.returned})` : ""}
          {r.input_truncated ? " · input sampled" : ""}
        </p>
      </div>
    );
  }

  if (r.kind === "series") {
    return (
      <div className="overflow-x-auto">
        <table className="text-xs">
          <tbody>
            {r.index?.slice(0, 50).map((idx, i) => (
              <tr key={i} className="border-t" style={{ borderColor: "var(--border)" }}>
                <td className="px-2 py-1 font-medium">{String(idx)}</td>
                <td className="px-2 py-1">{String(r.values?.[i] ?? "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-1 text-[11px] muted">{r.row_count} values</p>
      </div>
    );
  }

  if (r.kind === "list")
    return <p className="text-xs">{(r.values ?? []).slice(0, 100).join(", ")}</p>;

  return <p className="text-sm font-mono">{String(r.value)}</p>;
}

export function QueryConsole({ datasetId }: { datasetId: string }) {
  const [expr, setExpr] = useState(EXAMPLES[1]);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      setResult(await api.query(datasetId, expr));
    } catch (e: any) {
      setResult({ kind: "scalar", error: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-5">
      <h3 className="flex items-center gap-2 font-semibold">
        <Terminal size={16} className="text-brand" /> Query console
        <span className="chip">sandboxed</span>
      </h3>
      <p className="mt-1 text-sm muted">
        Run a pandas expression over <code>df</code>. Allow-listed methods only — the
        same tool an agent calls over MCP.
      </p>

      <div className="mt-3 flex gap-2">
        <input
          value={expr}
          onChange={(e) => setExpr(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          spellCheck={false}
          className="flex-1 rounded-lg border bg-transparent px-3 py-2 font-mono text-sm"
          style={{ borderColor: "var(--border)" }}
        />
        <button className="btn-primary" onClick={run} disabled={busy}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
        </button>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setExpr(ex)}
            className="rounded-full border px-2 py-0.5 text-[11px] muted hover:text-brand"
            style={{ borderColor: "var(--border)" }}
          >
            {ex.length > 46 ? ex.slice(0, 46) + "…" : ex}
          </button>
        ))}
      </div>

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 rounded-xl border p-3"
          style={{ borderColor: "var(--border)" }}
        >
          <ResultView r={result} />
        </motion.div>
      )}
    </div>
  );
}
