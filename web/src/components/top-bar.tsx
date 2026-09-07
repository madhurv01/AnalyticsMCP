"use client";

import { Moon, Sun, LogOut, Sparkles } from "lucide-react";
import { useTheme } from "./theme-provider";
import { api, type User } from "@/lib/api";

export function TopBar({ user }: { user: User | null }) {
  const { theme, toggle } = useTheme();
  return (
    <header className="sticky top-0 z-20 border-b backdrop-blur"
      style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--bg) 80%, transparent)" }}>
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <a href="/" className="flex items-center gap-2 font-semibold">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-white">
            <Sparkles size={16} />
          </span>
          InsightForge
        </a>
        <div className="flex items-center gap-2">
          <button onClick={toggle} className="btn-ghost !px-2.5" aria-label="Toggle theme">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          {user && (
            <>
              {user.picture_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={user.picture_url} alt="" className="h-8 w-8 rounded-full" />
              ) : (
                <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-100 text-brand-700 text-xs font-bold">
                  {user.email[0]?.toUpperCase()}
                </span>
              )}
              <button
                className="btn-ghost !px-2.5"
                onClick={async () => {
                  await api.logout();
                  location.href = "/";
                }}
              >
                <LogOut size={16} />
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
