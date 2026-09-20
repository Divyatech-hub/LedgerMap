import { useState } from "react";
import { correctLineItem, getRun } from "../api/client";
import type { Run, RunLineItem } from "../api/types";

interface ReviewTableProps {
  run: Run;
  onRunUpdated: (run: Run) => void;
}

const METHOD_LABELS: Record<string, string> = {
  exact: "Exact match",
  fuzzy: "Fuzzy match",
  inherited: "Inherited",
  review: "Needs review",
  corrected: "Manually corrected",
};

function methodClass(method: string): string {
  return method === "review" ? "method-review" : "method-confident";
}

function formatConfidence(confidence: string | null): string {
  if (confidence === null) return "—";
  const value = Number(confidence);
  return Number.isFinite(value) ? `${Math.round(value * 100)}%` : confidence;
}

export function ReviewTable({ run, onRunUpdated }: ReviewTableProps) {
  return (
    <section className="panel">
      <h2>
        Review — {run.period}{" "}
        <span className="counts">
          {run.resolved_rows}/{run.total_rows} resolved
          {run.review_rows > 0 ? `, ${run.review_rows} need review` : ""}
        </span>
      </h2>
      <div className="table-scroll">
        <table className="review-table">
          <thead>
            <tr>
              <th>Account</th>
              <th>Ancestors</th>
              <th>Amount</th>
              <th>Code</th>
              <th>Method</th>
              <th>Confidence</th>
              <th>Reason</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {run.line_items.map((item) => (
              <LineItemRow key={item.id} runId={run.id} item={item} onRunUpdated={onRunUpdated} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LineItemRow({
  runId,
  item,
  onRunUpdated,
}: {
  runId: number;
  item: RunLineItem;
  onRunUpdated: (run: Run) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [code, setCode] = useState(item.matched_code ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!code.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await correctLineItem(runId, item.id, { resulting_code: code.trim() });
      const updated = await getRun(runId);
      onRunUpdated(updated);
      setEditing(false);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr className={item.status === "review" ? "row-review" : undefined}>
      <td>{item.raw_name}</td>
      <td className="ancestors">{item.ancestors.join(" › ") || "—"}</td>
      <td className="amount">{item.amount}</td>
      <td>
        {editing ? (
          <input
            type="text"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            disabled={saving}
            autoFocus
          />
        ) : (
          item.matched_code ?? "—"
        )}
      </td>
      <td>
        <span className={methodClass(item.method)}>
          {METHOD_LABELS[item.method] ?? item.method}
        </span>
      </td>
      <td>{formatConfidence(item.confidence)}</td>
      <td className="reason">{item.review_reason ?? "—"}</td>
      <td>
        {editing ? (
          <>
            <button type="button" onClick={handleSave} disabled={saving || !code.trim()}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={() => {
                setEditing(false);
                setCode(item.matched_code ?? "");
                setError(null);
              }}
              disabled={saving}
            >
              Cancel
            </button>
          </>
        ) : (
          <button type="button" onClick={() => setEditing(true)}>
            {item.matched_code ? "Change" : "Assign code"}
          </button>
        )}
        {error && <p className="error">{error}</p>}
      </td>
    </tr>
  );
}
