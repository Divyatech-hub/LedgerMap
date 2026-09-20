import { useEffect, useState } from "react";
import { listClientRuns } from "../api/client";
import type { RunSummary } from "../api/types";

interface RunHistoryProps {
  clientId: number;
  refreshKey: number;
  selectedRunId: number | null;
  onSelect: (runId: number) => void;
}

export function RunHistory({
  clientId,
  refreshKey,
  selectedRunId,
  onSelect,
}: RunHistoryProps) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listClientRuns(clientId)
      .then(setRuns)
      .catch((err: unknown) => setError(String(err)));
  }, [clientId, refreshKey]);

  if (error) return <p className="error">{error}</p>;
  if (runs.length === 0) {
    return <p className="section-subtitle">No runs yet — upload a trial balance above.</p>;
  }

  return (
    <ul className="run-list">
      {runs.map((run) => (
        <li key={run.id}>
          <button
            type="button"
            className={run.id === selectedRunId ? "selected" : ""}
            onClick={() => onSelect(run.id)}
          >
            {run.period}
          </button>
        </li>
      ))}
    </ul>
  );
}
