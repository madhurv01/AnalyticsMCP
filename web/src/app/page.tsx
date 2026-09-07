"use client";

import { motion } from "framer-motion";
import { ArrowRight, BarChart3, FileSpreadsheet, ShieldCheck, Workflow } from "lucide-react";
import { api } from "@/lib/api";
import { TopBar } from "@/components/top-bar";

const features = [
  { icon: Workflow, title: "Real analytics workflow", body: "12 animated steps — schema detection, cleaning, relationship discovery, anomaly detection." },
  { icon: BarChart3, title: "Statistics that matter", body: "Pandas, SciPy & scikit-learn. Correlation, normality, IsolationForest outliers — no mock data." },
  { icon: FileSpreadsheet, title: "Premium Excel reports", body: "9 formatted sheets: exec dashboard, KPIs, correlation heatmaps, insights, native charts." },
  { icon: ShieldCheck, title: "Secure by default", body: "Google OAuth only, HttpOnly session cookies, per-user isolation, rate limiting." },
];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <TopBar user={null} />
      <main className="mx-auto max-w-6xl px-5">
        <section className="grid gap-8 py-20 md:grid-cols-2 md:items-center">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <span className="inline-block rounded-full border px-3 py-1 text-xs muted"
              style={{ borderColor: "var(--border)" }}>
              MCP-native · AI data analyst
            </span>
            <h1 className="mt-4 text-4xl font-bold leading-tight md:text-5xl">
              Drop a CSV.<br />Get a real analyst&rsquo;s report.
            </h1>
            <p className="mt-4 text-lg muted">
              InsightForge profiles your data, runs genuine statistical analysis, finds
              relationships and anomalies, and builds a premium multi-sheet Excel report.
            </p>
            <a href={api.loginUrl()} className="btn-primary mt-6">
              Continue with Google <ArrowRight size={16} />
            </a>
          </motion.div>

          <motion.div
            className="card p-6"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.15 }}
          >
            <div className="space-y-3">
              {["Loading dataset", "Detecting schema", "Discovering relationships", "Extracting insights", "Building Excel report"].map(
                (s, i) => (
                  <motion.div
                    key={s}
                    className="flex items-center gap-3 rounded-lg border p-3 text-sm"
                    style={{ borderColor: "var(--border)" }}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 + i * 0.12 }}
                  >
                    <span className="h-2 w-2 rounded-full bg-brand" />
                    {s}
                  </motion.div>
                ),
              )}
            </div>
          </motion.div>
        </section>

        <section className="grid gap-4 pb-24 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              className="card p-5"
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              <f.icon size={20} className="text-brand" />
              <h3 className="mt-3 font-semibold">{f.title}</h3>
              <p className="mt-1 text-sm muted">{f.body}</p>
            </motion.div>
          ))}
        </section>
      </main>
    </div>
  );
}
