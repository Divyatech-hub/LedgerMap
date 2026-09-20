import { getMisExportUrl } from "../api/client";
import type { Client, Run } from "../api/types";

interface RunSummaryBarProps {
  client: Client;
  run: Run | null;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function RunSummaryBar({ client, run }: RunSummaryBarProps) {
  return (
    <div className="summary-bar">
      <div className="summary-identity">
        <h2 className="summary-client-name">{client.name}</h2>
        {run ? (
          <span className="summary-meta">
            {run.period} · uploaded {formatDate(run.created_at)}
            {run.original_filename ? ` · ${run.original_filename}` : ""}
          </span>
        ) : (
          <span className="summary-meta">No run selected</span>
        )}
      </div>

      {run && (
        <div className="summary-stats">
          <Stat label="Total accounts" value={run.total_rows} />
          <Stat label="Resolved" value={run.resolved_rows} tone="good" />
          <Stat
            label="Needs review"
            value={run.review_rows}
            tone={run.review_rows > 0 ? "warn" : "good"}
          />
        </div>
      )}

      <a
        className="export-button"
        href={getMisExportUrl(client.id)}
        aria-disabled={!run}
        onClick={(event) => {
          if (!run) event.preventDefault();
        }}
      >
        Export Detailed MIS (.xlsx)
      </a>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "good" | "warn";
}) {
  return (
    <div className={`stat ${tone ? `stat-${tone}` : ""}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
