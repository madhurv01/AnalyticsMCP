"use client";

import { motion } from "framer-motion";

const GRADE_COLOR: Record<string, string> = {
  A: "#22c55e",
  B: "#4ade80",
  C: "#facc15",
  D: "#fb923c",
  E: "#f87171",
  F: "#ef4444",
};

export function QualityGauge({
  score,
  grade,
  size = 148,
}: {
  score: number;
  grade: string;
  size?: number;
}) {
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const color = GRADE_COLOR[grade] ?? "#6366f1";

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          className="text-black/5 dark:text-white/10"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c - c * pct }}
          transition={{ duration: 1, ease: "easeOut" }}
          style={{ filter: `drop-shadow(0 0 8px ${color}aa)` }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <motion.span
          className="text-3xl font-bold glow-text"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          style={{ color }}
        >
          {Math.round(score)}
        </motion.span>
        <span className="text-xs muted">grade {grade}</span>
      </div>
    </div>
  );
}
