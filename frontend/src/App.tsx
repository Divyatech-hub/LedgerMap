import { useState } from "react";
import { getRun } from "./api/client";
import type { Client, Run } from "./api/types";
import { ClientPicker } from "./components/ClientPicker";
import { ReviewTable } from "./components/ReviewTable";
import { RunHistory } from "./components/RunHistory";
import { UploadForm } from "./components/UploadForm";

export function App() {
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [runsRefreshKey, setRunsRefreshKey] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);

  function handleClientSelect(client: Client) {
    setSelectedClient(client);
    setRun(null);
  }

  function handleRunUploaded(newRun: Run) {
    setRun(newRun);
    setRunsRefreshKey((key) => key + 1);
  }

  async function handleSelectRun(runId: number) {
    setLoadError(null);
    try {
      const fetched = await getRun(runId);
      setRun(fetched);
    } catch (err) {
      setLoadError(String(err));
    }
  }

  return (
    <main className="app">
      <header>
        <h1>LedgerMap</h1>
        <p className="tagline">Trial balance → IFRS-coded MIS mapping, reviewed before it counts.</p>
      </header>

      <div className="layout">
        <div className="sidebar">
          <ClientPicker selectedClientId={selectedClient?.id ?? null} onSelect={handleClientSelect} />

          {selectedClient && (
            <>
              <UploadForm clientId={selectedClient.id} onUploaded={handleRunUploaded} />
              <section className="panel">
                <h2>Runs</h2>
                <RunHistory
                  clientId={selectedClient.id}
                  refreshKey={runsRefreshKey}
                  selectedRunId={run?.id ?? null}
                  onSelect={handleSelectRun}
                />
              </section>
            </>
          )}
        </div>

        <div className="content">
          {!selectedClient && <p>Select or add a client to get started.</p>}
          {selectedClient && !run && <p>Upload a trial balance or pick a run to review it.</p>}
          {loadError && <p className="error">{loadError}</p>}
          {run && <ReviewTable run={run} onRunUpdated={setRun} />}
        </div>
      </div>
    </main>
  );
}
