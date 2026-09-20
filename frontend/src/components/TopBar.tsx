import type { Client } from "../api/types";

interface TopBarProps {
  client: Client | null;
  onSwitchClient: () => void;
}

export function TopBar({ client, onSwitchClient }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <h1>LedgerMap</h1>
        <p className="tagline">
          Trial balance → IFRS-coded MIS mapping, reviewed before it counts.
        </p>
      </div>
      {client && (
        <button type="button" className="client-switch" onClick={onSwitchClient}>
          <span className="client-switch-label">Client</span>
          <span className="client-switch-name">{client.name}</span>
          <span className="client-switch-chevron" aria-hidden="true">
            ⇄
          </span>
        </button>
      )}
    </header>
  );
}
