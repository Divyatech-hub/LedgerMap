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

  if (loading) return <div className="empty-state">Loading Detailed MIS…</div>;
  if (error) return <p className="error">{error}</p>;
  if (!report || report.periods.length === 0) {
    return <div className="empty-state">Upload a trial balance to see the Detailed MIS here.</div>;
  }

  return (
    <section className="panel">
      <h2>Detailed MIS</h2>
      <p className="section-subtitle">
        Every resolved account, rolled up by code, one column per period.
      </p>
      {report.unresolved_periods.length > 0 && (
        <p className="mis-note">
          <span aria-hidden="true">●</span>
          Still awaiting review: {report.unresolved_periods.join(", ")}
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
