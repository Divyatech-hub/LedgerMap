import { useState } from "react";
import { chatCorrectRun, correctLineItem, getRun } from "../api/client";
import type { ChatCandidate, Run } from "../api/types";

interface ChatPanelProps {
  run: Run;
  onRunUpdated: (run: Run) => void;
}

interface ChatEntry {
  id: number;
  role: "user" | "assistant";
  text: string;
  candidates?: ChatCandidate[];
}

let nextEntryId = 1;

export function ChatPanel({ run, onRunUpdated }: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;

    setEntries((prev) => [...prev, { id: nextEntryId++, role: "user", text: trimmed }]);
    setMessage("");
    setSending(true);
    setError(null);

    try {
      const response = await chatCorrectRun(run.id, trimmed);
      setEntries((prev) => [
        ...prev,
        {
          id: nextEntryId++,
          role: "assistant",
          text: response.explanation || (response.applied ? "Done." : "I couldn't apply that."),
          candidates: response.applied ? undefined : response.candidates,
        },
      ]);
      if (response.applied) {
        const updated = await getRun(run.id);
        onRunUpdated(updated);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setSending(false);
    }
  }

  async function handlePickCandidate(candidate: ChatCandidate, code: string) {
    if (!code.trim()) return;
    setSending(true);
    setError(null);
    try {
      await correctLineItem(run.id, candidate.id, { resulting_code: code.trim() });
      const updated = await getRun(run.id);
      onRunUpdated(updated);
      setEntries((prev) => [
        ...prev,
        {
          id: nextEntryId++,
          role: "assistant",
          text: `Applied: ${candidate.raw_name} → ${code.trim()}.`,
        },
      ]);
    } catch (err) {
      setError(String(err));
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="panel chat-panel">
      <h2>Chat corrections</h2>
      <p className="chat-hint">
        Try: “Business Credit Card should be 2069 not 2068”
      </p>
      <div className="chat-log">
        {entries.length === 0 && <p className="chat-empty">No messages yet.</p>}
        {entries.map((entry) => (
          <div key={entry.id} className={`chat-entry chat-entry-${entry.role}`}>
            <p>{entry.text}</p>
            {entry.candidates && entry.candidates.length > 0 && (
              <ul className="chat-candidates">
                {entry.candidates.map((candidate) => (
                  <ChatCandidateRow
                    key={candidate.id}
                    candidate={candidate}
                    disabled={sending}
                    onPick={(code) => handlePickCandidate(candidate, code)}
                  />
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit} className="chat-form">
        <input
          type="text"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Describe a correction in plain language…"
          disabled={sending}
        />
        <button type="submit" disabled={sending || !message.trim()}>
          {sending ? "Sending…" : "Send"}
        </button>
      </form>
    </section>
  );
}

function ChatCandidateRow({
  candidate,
  disabled,
  onPick,
}: {
  candidate: ChatCandidate;
  disabled: boolean;
  onPick: (code: string) => void;
}) {
  const [code, setCode] = useState("");

  return (
    <li className="chat-candidate">
      <span>
        {candidate.raw_name}
        {candidate.ancestors.length > 0 && (
          <span className="chat-candidate-ancestors"> ({candidate.ancestors.join(" › ")})</span>
        )}
        {candidate.matched_code && (
          <span className="chat-candidate-code"> — currently {candidate.matched_code}</span>
        )}
      </span>
      <input
        type="text"
        placeholder="code"
        value={code}
        onChange={(event) => setCode(event.target.value)}
        disabled={disabled}
      />
      <button type="button" onClick={() => onPick(code)} disabled={disabled || !code.trim()}>
        Apply
      </button>
    </li>
  );
}
