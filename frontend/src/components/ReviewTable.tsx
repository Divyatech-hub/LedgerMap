import { useMemo, useState } from "react";
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
  llm: "AI suggested",
  corrected: "Corrected",
  review: "Needs review",
};

const REASON_LABELS: Record<string, string> = {
  low_fuzzy_confidence: "No confident match found",
  no_mapping_candidates: "No mapping history for this client yet",
};

type FilterMode = "all" | "review";

function methodTone(method: string): "confident" | "review" {
  return method === "review" ? "review" : "confident";
}

function formatConfidence(confidence: string | null): string {
  if (confidence === null) return "—";
  const value = Number(confidence);
  return Number.isFinite(value) ? `${Math.round(value * 100)}%` : confidence;
}

function formatReason(reason: string | null): string {
  if (!reason) return "—";
  return REASON_LABELS[reason] ?? reason.replaceAll("_", " ");
}

export function ReviewTable({ run, onRunUpdated }: ReviewTableProps) {
  const [filter, setFilter] = useState<FilterMode>("all");
  const [search, setSearch] = useState("");

  const visibleItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    return run.line_items
      .filter((item) => filter === "all" || item.status === "review")
      .filter((item) => !query || item.raw_name.toLowerCase().includes(query))
      .sort((a, b) => {
        // Items still needing review float to the top so the accountant
        // sees what needs attention first, without losing the original
        // (row-number) order within each group.
        if (a.status === b.status) return (a.row_number ?? 0) - (b.row_number ?? 0);
        return a.status === "review" ? -1 : 1;
      });
  }, [run.line_items, filter, search]);

  const isFiltered = filter !== "all" || search.trim() !== "";

  return (
    <section className="panel">
      <div className="review-header">
        <div>
          <h2>Review</h2>
          <p className="section-subtitle">
            {run.resolved_rows} of {run.total_rows} accounts resolved
            {run.review_rows > 0 ? ` · ${run.review_rows} need a code` : ""}
          </p>
        </div>
        <div className="review-controls">
          <input
            type="search"
            placeholder="Search accounts…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <div className="segmented">
            <button
              type="button"
              className={filter === "all" ? "selected" : ""}
              onClick={() => setFilter("all")}
            >
              All <span className="segmented-count">{run.total_rows}</span>
            </button>
            <button
              type="button"
              className={filter === "review" ? "selected" : ""}
              onClick={() => setFilter("review")}
              disabled={run.review_rows === 0}
            >
              Needs review <span className="segmented-count">{run.review_rows}</span>
            </button>
          </div>
        </div>
      </div>

      {run.review_rows === 0 && (
        <p className="all-clear">
          <span className="all-clear-dot" aria-hidden="true" />
          Every account resolved to a code. Nothing left to review.
        </p>
      )}

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
              <th>Why</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visibleItems.map((item) => (
              <LineItemRow key={item.id} runId={run.id} item={item} onRunUpdated={onRunUpdated} />
            ))}
            {visibleItems.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-row">
                  {isFiltered ? "No accounts match your filter." : "No line items in this run."}
                </td>
              </tr>
            )}
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
        <span className={`pill pill-${methodTone(item.method)}`}>
          {METHOD_LABELS[item.method] ?? item.method}
        </span>
      </td>
      <td className="amount">{formatConfidence(item.confidence)}</td>
      <td className="reason">{formatReason(item.review_reason)}</td>
      <td className="row-actions">
        {editing ? (
          <>
            <button type="button" onClick={handleSave} disabled={saving || !code.trim()}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              className="button-ghost"
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
          <button type="button" className="button-ghost" onClick={() => setEditing(true)}>
            {item.matched_code ? "Change" : "Assign code"}
          </button>
        )}
        {error && <p className="error">{error}</p>}
      </td>
    </tr>
  );
}
