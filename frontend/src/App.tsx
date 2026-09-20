import { useState } from "react";
import { getRun } from "./api/client";
import type { Client, Run } from "./api/types";
import { ChatPanel } from "./components/ChatPanel";
import { ClientPicker } from "./components/ClientPicker";
import { MisPreview } from "./components/MisPreview";
import { ReviewTable } from "./components/ReviewTable";
import { RunHistory } from "./components/RunHistory";
import { RunSummaryBar } from "./components/RunSummaryBar";
import { UploadForm } from "./components/UploadForm";

type ContentTab = "review" | "mis" | "chat";

export function App() {
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [runsRefreshKey, setRunsRefreshKey] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTab] = useState<ContentTab>("review");

  function handleClientSelect(client: Client) {
    setSelectedClient(client);
    setRun(null);
    setLoadError(null);
  }

  function handleRunUploaded(newRun: Run) {
    setRun(newRun);
    setRunsRefreshKey((key) => key + 1);
    setTab("review");
  }

  async function handleSelectRun(runId: number) {
    setLoadError(null);
    setTab("review");
    try {
      const fetched = await getRun(runId);
      setRun(fetched);
    } catch (err) {
      setLoadError(String(err));
    }
  }

  return (
    <main className="app">
      <header className="app-header">
        <h1>LedgerMap</h1>
        <p className="tagline">
          Trial balance → IFRS-coded MIS mapping, reviewed before it counts.
        </p>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <ClientPicker
            selectedClientId={selectedClient?.id ?? null}
            onSelect={handleClientSelect}
          />

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
        </aside>

        <div className="content">
          {!selectedClient && (
            <div className="empty-state">
              <p>Select a client on the left, or add a new one, to get started.</p>
            </div>
          )}

          {selectedClient && (
            <>
              <RunSummaryBar client={selectedClient} run={run} />

              <div className="tabs">
                <button
                  type="button"
                  className={tab === "review" ? "selected" : ""}
                  onClick={() => setTab("review")}
                >
                  Review
                </button>
                <button
                  type="button"
                  className={tab === "mis" ? "selected" : ""}
                  onClick={() => setTab("mis")}
                >
                  Detailed MIS
                </button>
                <button
                  type="button"
                  className={tab === "chat" ? "selected" : ""}
                  onClick={() => setTab("chat")}
                  disabled={!run}
                  title={run ? undefined : "Upload or select a run first"}
                >
                  Chat corrections
                </button>
              </div>

              {loadError && <p className="error">{loadError}</p>}

              {tab === "review" &&
                (run ? (
                  <ReviewTable run={run} onRunUpdated={setRun} />
                ) : (
                  <div className="empty-state">
                    <p>Upload a trial balance or pick a run from the sidebar to review it.</p>
                  </div>
                ))}

              {tab === "mis" && (
                <MisPreview clientId={selectedClient.id} refreshKey={runsRefreshKey} />
              )}

              {tab === "chat" &&
                (run ? (
                  <ChatPanel run={run} onRunUpdated={setRun} />
                ) : (
                  <div className="empty-state">
                    <p>Select a run before starting a chat correction.</p>
                  </div>
                ))}
            </>
          )}
        </div>
      </div>
    </main>
  );
}
