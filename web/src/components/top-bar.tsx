"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Moon, Sun, LogOut, Sparkles, ChevronDown } from "lucide-react";
import { useTheme } from "./theme-provider";
import { api, type User } from "@/lib/api";

function initialFor(user: User) {
  const src = user.name?.trim() || user.email;
  return src.charAt(0).toUpperCase();
}

export function UserBadge({ user }: { user: User }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="btn-ghost !gap-2 !py-1.5 !pl-1.5 !pr-2.5"
      >
        <span
          className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-sm font-bold text-white shadow-glow-sm ring-1 ring-white/25"
          title={user.email}
        >
          {initialFor(user)}
        </span>
        <span className="hidden max-w-[160px] truncate text-sm sm:block">
          {user.email}
        </span>
        <ChevronDown size={14} className="muted" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.14 }}
            className="card absolute right-0 mt-2 w-64 overflow-hidden p-0"
          >
            <div className="flex items-center gap-3 border-b p-3" style={{ borderColor: "var(--border)" }}>
              <span className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-base font-bold text-white shadow-glow-sm ring-1 ring-white/25">
                {initialFor(user)}
              </span>
              <div className="min-w-0">
                {user.name && <p className="truncate text-sm font-medium">{user.name}</p>}
                <p className="truncate text-xs muted">{user.email}</p>
              </div>
            </div>
            <button
              className="flex w-full items-center gap-2 p-3 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5"
              onClick={async () => {
                await api.logout();
                location.href = "/";
              }}
            >
              <LogOut size={15} /> Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function TopBar({ user }: { user: User | null }) {
  const { theme, toggle } = useTheme();
  return (
    <header
      className="sticky top-0 z-30 border-b backdrop-blur-md"
      style={{
        borderColor: "var(--border)",
        background: "color-mix(in srgb, var(--bg) 78%, transparent)",
      }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
        <a href="/" className="flex items-center gap-2 font-semibold">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 text-white shadow-glow-sm">
            <Sparkles size={16} />
          </span>
          <span className="glow-text">InsightForge</span>
        </a>
        <div className="flex items-center gap-2">
          <button onClick={toggle} className="btn-ghost !px-2.5" aria-label="Toggle theme">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          {user && <UserBadge user={user} />}
        </div>
      </div>
    </header>
  );
}
