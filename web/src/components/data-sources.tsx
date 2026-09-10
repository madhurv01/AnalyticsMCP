"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plug, Plus, Trash2, Download, Loader2, ChevronRight, Server } from "lucide-react";
import { api, type Catalog, type Connection } from "@/lib/api";

export function DataSources({ onImported }: { onImported: (datasetId: string) => void }) {
  const [conns, setConns] = useState<Connection[]>([]);
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", url: "", auth_token: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [importing, setImporting] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [argsText, setArgsText] = useState("{}");

  const load = useCallback(() => {
    api.connections().then(setConns).catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const c = await api.addConnection({
        name: form.name,
        url: form.url,
        auth_token: form.auth_token || undefined,
      });
      setCatalog(c);
      setForm({ name: "", url: "", auth_token: "" });
      setAdding(false);
      load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function openCatalog(id: string) {
    setErr(null);
    setCatalog(null);
    try {
      setCatalog(await api.catalog(id));
    } catch (e: any) {
      setErr(e.message);
    }
  }

  function selectTool(toolName: string, schema: any) {
    // seed the args editor from the tool's JSON schema
    const args: Record<string, any> = {};
    const props = schema?.properties ?? {};
    const required: string[] = schema?.required ?? [];
    for (const [k, v] of Object.entries<any>(props)) {
      if (v.default !== undefined) args[k] = v.default;
      else if (required.includes(k)) {
        args[k] =
          v.type === "integer" || v.type === "number" ? 100 : v.type === "boolean" ? false : "";
      }
    }
    setSelectedTool(toolName);
    setArgsText(JSON.stringify(args, null, 2));
    setErr(null);
  }

  async function runImport(connId: string, toolName: string) {
    let args: any = {};
    try {
      args = argsText.trim() ? JSON.parse(argsText) : {};
    } catch {
      setErr("arguments must be valid JSON");
      return;
    }
    setImporting(toolName);
    setErr(null);
    try {
      const ds = await api.importDataset(connId, {
        mode: "tool",
        tool_name: toolName,
        arguments: args,
      });
      onImported(ds.id);
      setCatalog(null);
      setSelectedTool(null);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setImporting(null);
    }
  }

  return (
    <div className="card p-5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between"
      >
        <h3 className="flex items-center gap-2 font-semibold">
          <Plug size={16} className="text-brand" /> Data sources
          <span className="chip">{conns.length} MCP</span>
        </h3>
        <ChevronRight
          size={16}
          className={`muted transition-transform ${open ? "rotate-90" : ""}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <p className="mt-2 text-sm muted">
              Connect an external MCP server and pull a table straight into the
              pipeline — no CSV export.
            </p>

            <ul className="mt-3 space-y-2">
              {conns.map((c) => (
                <li
                  key={c.id}
                  className="rounded-xl border p-3 text-sm"
                  style={{ borderColor: "var(--border)" }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <Server size={14} className="shrink-0 text-brand" />
                      <div className="min-w-0">
                        <p className="truncate font-medium">{c.name}</p>
                        <p className="truncate text-xs muted">{c.url}</p>
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button
                        className="btn-ghost !p-1.5"
                        onClick={() => openCatalog(c.id)}
                        title="Browse & import"
                      >
                        <Download size={13} />
                      </button>
                      <button
                        className="btn-ghost !p-1.5"
                        onClick={async () => {
                          await api.deleteConnection(c.id);
                          load();
                        }}
                        title="Remove"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {catalog?.connection.id === c.id && (
                    <div className="mt-3 space-y-1.5 border-t pt-3" style={{ borderColor: "var(--border)" }}>
                      <p className="text-xs font-semibold uppercase tracking-wide muted">
                        Importable tools ({catalog.tools.length})
                      </p>
                      <div className="max-h-64 space-y-1.5 overflow-y-auto scroll-thin">
                        {catalog.tools.map((t) => (
                          <div key={t.name}>
                            <button
                              onClick={() =>
                                selectedTool === t.name
                                  ? setSelectedTool(null)
                                  : selectTool(t.name, t.input_schema)
                              }
                              className={`flex w-full items-center justify-between gap-2 rounded-lg border p-2 text-left text-xs ${
                                selectedTool === t.name ? "border-brand" : ""
                              }`}
                              style={selectedTool === t.name ? {} : { borderColor: "var(--border)" }}
                            >
                              <span className="min-w-0">
                                <span className="font-medium">{t.name}</span>
                                <span className="block truncate muted">{t.description}</span>
                              </span>
                              <ChevronRight
                                size={13}
                                className={`shrink-0 transition-transform ${
                                  selectedTool === t.name ? "rotate-90 text-brand" : "muted"
                                }`}
                              />
                            </button>
                            {selectedTool === t.name && (
                              <div className="mt-1.5 space-y-1.5 rounded-lg border p-2"
                                style={{ borderColor: "var(--border)" }}>
                                <label className="text-[11px] muted">Arguments (JSON)</label>
                                <textarea
                                  value={argsText}
                                  onChange={(e) => setArgsText(e.target.value)}
                                  spellCheck={false}
                                  rows={Math.min(8, argsText.split("\n").length + 1)}
                                  className="w-full rounded-md border bg-transparent p-2 font-mono text-[11px]"
                                  style={{ borderColor: "var(--border)" }}
                                />
                                <button
                                  className="btn-primary w-full !py-1.5 text-xs"
                                  disabled={!!importing}
                                  onClick={() => runImport(c.id, t.name)}
                                >
                                  {importing === t.name ? (
                                    <Loader2 size={13} className="animate-spin" />
                                  ) : (
                                    <>
                                      <Download size={13} /> Import &amp; analyze
                                    </>
                                  )}
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                      {catalog.tools.length === 0 && (
                        <p className="text-xs muted">This server exposes no tools.</p>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>

            {err && <p className="mt-2 text-xs text-rose-500">{err}</p>}

            {adding ? (
              <form onSubmit={add} className="mt-3 space-y-2">
                {(["name", "url"] as const).map((k) => (
                  <input
                    key={k}
                    required
                    placeholder={k === "url" ? "http://sample-mcp:9100/mcp" : "My warehouse"}
                    value={form[k]}
                    onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                    className="w-full rounded-lg border bg-transparent px-3 py-2 text-sm"
                    style={{ borderColor: "var(--border)" }}
                  />
                ))}
                <input
                  placeholder="Bearer token (optional)"
                  value={form.auth_token}
                  onChange={(e) => setForm({ ...form, auth_token: e.target.value })}
                  className="w-full rounded-lg border bg-transparent px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border)" }}
                />
                <div className="flex gap-2">
                  <button className="btn-primary flex-1" disabled={busy}>
                    {busy ? <Loader2 size={15} className="animate-spin" /> : "Connect"}
                  </button>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setAdding(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button className="btn-ghost mt-3 w-full" onClick={() => setAdding(true)}>
                <Plus size={15} /> Connect an MCP server
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
