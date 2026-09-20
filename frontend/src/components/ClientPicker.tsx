import { useEffect, useState } from "react";
import { createClient, listClients } from "../api/client";
import type { Client } from "../api/types";

interface ClientPickerProps {
  selectedClientId: number | null;
  onSelect: (client: Client) => void;
}

export function ClientPicker({ selectedClientId, onSelect }: ClientPickerProps) {
  const [clients, setClients] = useState<Client[]>([]);
  const [newName, setNewName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listClients()
      .then(setClients)
      .catch((err: unknown) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const client = await createClient(newName.trim());
      setClients((prev) => [...prev, client].sort((a, b) => a.name.localeCompare(b.name)));
      setNewName("");
      onSelect(client);
    } catch (err) {
      setError(String(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <section className="panel">
      <h2>Client</h2>
      {loading && <p>Loading clients…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && clients.length > 0 && (
        <ul className="client-list">
          {clients.map((client) => (
            <li key={client.id}>
              <button
                type="button"
                className={client.id === selectedClientId ? "selected" : ""}
                onClick={() => onSelect(client)}
              >
                {client.name}
              </button>
            </li>
          ))}
        </ul>
      )}
      {!loading && clients.length === 0 && <p>No clients yet — add one below.</p>}
      <form onSubmit={handleCreate} className="inline-form">
        <input
          type="text"
          placeholder="New client name"
          value={newName}
          onChange={(event) => setNewName(event.target.value)}
          disabled={creating}
        />
        <button type="submit" disabled={creating || !newName.trim()}>
          {creating ? "Adding…" : "Add client"}
        </button>
      </form>
    </section>
  );
}
