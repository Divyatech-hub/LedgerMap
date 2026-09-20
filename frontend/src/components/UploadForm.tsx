import { useState } from "react";
import { uploadRun } from "../api/client";
import type { Run } from "../api/types";

interface UploadFormProps {
  clientId: number;
  onUploaded: (run: Run) => void;
}

function currentPeriod(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function UploadForm({ clientId, onUploaded }: UploadFormProps) {
  const [period, setPeriod] = useState(currentPeriod());
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const run = await uploadRun(clientId, period, file);
      onUploaded(run);
      setFile(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Upload trial balance</h2>
      <form onSubmit={handleSubmit} className="upload-form">
        <label>
          Period
          <input
            type="text"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            placeholder="2024-01"
            required
          />
        </label>
        <label>
          Workbook (.xlsx)
          <input
            type="file"
            accept=".xlsx,.xls"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
          />
        </label>
        <button type="submit" disabled={uploading || !file}>
          {uploading ? "Processing…" : "Upload and run"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
