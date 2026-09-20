import { useEffect, useMemo, useState } from "react";
import { createClient, listClients } from "../api/client";
import type { Client } from "../api/types";

interface ClientsPageProps {
  onSelect: (client: Client) => void;
}

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function ClientsPage({ onSelect }: ClientsPageProps) {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    listClients()
      .then(setClients)
      .catch((err: unknown) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  const visibleClients = useMemo(() => {
    const query = search.trim().toLowerCase();
    return clients
      .filter((client) => !query || client.name.toLowerCase().includes(query))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [clients, search]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const client = await createClient(newName.trim());
      setClients((prev) => [...prev, client]);
      setNewName("");
      setShowAddForm(false);
      onSelect(client);
    } catch (err) {
      setCreateError(String(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="clients-page">
      <div className="clients-page-header">
        <div>
          <h1 className="clients-page-title">Clients</h1>
          <p className="section-subtitle">
            {clients.length === 0
              ? "No clients yet."
              : `${clients.length} client${clients.length === 1 ? "" : "s"}`}
          </p>
        </div>
        <div className="clients-page-actions">
          <input
            type="search"
            placeholder="Search clients…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <button type="submit" onClick={() => setShowAddForm((prev) => !prev)}>
            {showAddForm ? "Cancel" : "Add client"}
          </button>
        </div>
      </div>

      {showAddForm && (
        <form onSubmit={handleCreate} className="inline-form add-client-form">
          <input
            type="text"
            placeholder="Client name"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            disabled={creating}
            autoFocus
          />
          <button type="submit" disabled={creating || !newName.trim()}>
            {creating ? "Adding…" : "Create"}
          </button>
          {createError && <p className="error">{createError}</p>}
        </form>
      )}

      {error && <p className="error">{error}</p>}

      {loading && <div className="empty-state">Loading clients…</div>}

      {!loading && clients.length === 0 && !showAddForm && (
        <div className="empty-state">
          <p>No clients yet. Add your first client to get started.</p>
          <button type="submit" onClick={() => setShowAddForm(true)}>
            Add client
          </button>
        </div>
      )}

      {!loading && clients.length > 0 && (
        <div className="client-grid">
          {visibleClients.map((client) => (
            <button
              type="button"
              key={client.id}
              className="client-card"
              onClick={() => onSelect(client)}
            >
              <span className="client-card-avatar">{initials(client.name)}</span>
              <span className="client-card-body">
                <span className="client-card-name">{client.name}</span>
                <span className="client-card-meta">
                  Added {formatDate(client.created_at)}
                </span>
              </span>
            </button>
          ))}
          {visibleClients.length === 0 && (
            <p className="section-subtitle">No clients match “{search}”.</p>
          )}
        </div>
      )}
    </div>
  );
}
