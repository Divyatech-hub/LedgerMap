import { useEffect, useState } from "react";
import { chatCorrectRun, correctLineItem, getChatMessages, getRun } from "../api/client";
import type { ChatCandidate, ChatMessage, Run } from "../api/types";

interface ChatPanelProps {
  run: Run;
  onRunUpdated: (run: Run) => void;
}

export function ChatPanel({ run, onRunUpdated }: ChatPanelProps) {
  const [message, setMessage] = useState("");
  // The server keeps the conversation; this is always its latest copy.
  const [entries, setEntries] = useState<ChatMessage[]>([]);
  // Shown while a message is in flight, before the server has stored it.
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEntries([]);
    setError(null);
    getChatMessages(run.id)
      .then((messages) => {
        if (!cancelled) setEntries(messages);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [run.id]);

  async function refreshAfterChange(applied: boolean) {
    const [messages, updatedRun] = await Promise.all([
      getChatMessages(run.id),
      applied ? getRun(run.id) : Promise.resolve(null),
    ]);
    setEntries(messages);
    if (updatedRun) onRunUpdated(updatedRun);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;

    setPendingText(trimmed);
    setMessage("");
    setSending(true);
    setError(null);

    try {
      const response = await chatCorrectRun(run.id, trimmed);
      await refreshAfterChange(response.applied);
    } catch (err) {
      setError(String(err));
    } finally {
      setPendingText(null);
      setSending(false);
    }
  }

  async function handlePickCandidate(
    candidate: ChatCandidate,
    code: string,
    originatingMessage: string | undefined,
  ) {
    if (!code.trim()) return;
    setSending(true);
    setError(null);
    try {
      // Passing the chat message that led here links the correction to the
      // conversation, and has the server add the "Applied" note to it.
      await correctLineItem(run.id, candidate.id, {
        resulting_code: code.trim(),
        chat_message: originatingMessage,
      });
      await refreshAfterChange(true);
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
        {entries.length === 0 && !pendingText && (
          <p className="chat-empty">No messages yet.</p>
        )}
        {entries.map((entry, index) => (
          <div key={entry.id} className={`chat-entry chat-entry-${entry.role}`}>
            <p>{entry.text}</p>
            {entry.candidates && entry.candidates.length > 0 && (
              <ul className="chat-candidates">
                {entry.candidates.map((candidate) => (
                  <ChatCandidateRow
                    key={candidate.id}
                    candidate={candidate}
                    disabled={sending}
                    onPick={(code) =>
                      handlePickCandidate(
                        candidate,
                        code,
                        precedingUserText(entries, index),
                      )
                    }
                  />
                ))}
              </ul>
            )}
          </div>
        ))}
        {pendingText && (
          <div className="chat-entry chat-entry-user">
            <p>{pendingText}</p>
          </div>
        )}
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

function precedingUserText(entries: ChatMessage[], index: number): string | undefined {
  for (let i = index - 1; i >= 0; i--) {
    if (entries[i].role === "user") return entries[i].text;
  }
  return undefined;
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
