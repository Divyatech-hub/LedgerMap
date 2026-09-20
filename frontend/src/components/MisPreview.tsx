import { useEffect, useState } from "react";
import { getClientMisReport } from "../api/client";
import type { MisReport } from "../api/types";

interface MisPreviewProps {
  clientId: number;
  refreshKey: number;
}

function cellClass(method: string): string {
  return method === "review" ? "mis-cell-review" : "mis-cell-confident";
}

export function MisPreview({ clientId, refreshKey }: MisPreviewProps) {
  const [report, setReport] = useState<MisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getClientMisReport(clientId)
      .then(setReport)
      .catch((err: unknown) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [clientId, refreshKey]);

  if (loading) return <p>Loading MIS preview…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!report || report.periods.length === 0) {
    return <p>No completed runs yet for this client.</p>;
  }

  return (
    <section className="panel">
      <h2>Detailed MIS preview</h2>
      {report.unresolved_periods.length > 0 && (
        <p className="mis-note">
          Periods with items still awaiting review:{" "}
          {report.unresolved_periods.join(", ")}
        </p>
      )}
      <div className="table-scroll">
        <table className="mis-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Description</th>
              {report.periods.map((period) => (
                <th key={period}>{period}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.rows.map((row) => (
              <tr key={row.code}>
                <td>{row.code}</td>
                <td className="mis-description">{row.description ?? "—"}</td>
                {report.periods.map((period) => {
                  const cell = row.cells[period];
                  return (
                    <td key={period} className={cell ? cellClass(cell.method) : undefined}>
                      {cell ? Number(cell.amount).toLocaleString() : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mis-legend">
        <span className="mis-cell-confident legend-swatch" /> exact / fuzzy / corrected{" "}
        <span className="mis-cell-review legend-swatch" /> still under review
      </p>
    </section>
  );
}
