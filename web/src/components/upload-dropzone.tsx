"use client";

import { motion } from "framer-motion";
import { UploadCloud, Loader2 } from "lucide-react";
import { useRef, useState } from "react";

export function UploadDropzone({
  onFile,
  busy,
}: {
  onFile: (f: File) => void;
  busy: boolean;
}) {
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function handle(files: FileList | null) {
    const f = files?.[0];
    if (f && f.name.toLowerCase().endsWith(".csv")) onFile(f);
  }

  return (
    <motion.div
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        handle(e.dataTransfer.files);
      }}
      onClick={() => input.current?.click()}
      animate={{ borderColor: drag ? "#4F46E5" : "var(--border)", scale: drag ? 1.01 : 1 }}
      className="card flex cursor-pointer flex-col items-center justify-center gap-3 border-2 border-dashed p-10 text-center"
    >
      <input
        ref={input}
        type="file"
        accept=".csv,text/csv"
        hidden
        onChange={(e) => handle(e.target.files)}
      />
      <span className="grid h-12 w-12 place-items-center rounded-xl bg-brand-100 text-brand-700">
        {busy ? <Loader2 className="animate-spin" /> : <UploadCloud />}
      </span>
      <div>
        <p className="font-medium">
          {busy ? "Uploading…" : "Drop a CSV file here"}
        </p>
        <p className="text-sm muted">or click to browse — up to 100 MB</p>
      </div>
    </motion.div>
  );
}
