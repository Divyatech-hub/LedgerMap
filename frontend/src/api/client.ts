import type {
  ApiErrorBody,
  Client,
  Correction,
  MisReport,
  Run,
  RunSummary,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as ApiErrorBody;
      detail = body.detail ?? detail;
    } catch {
      // response had no JSON body; fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function listClients(): Promise<Client[]> {
  return request<Client[]>("/clients");
}

export function createClient(name: string): Promise<Client> {
  return request<Client>("/clients", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function listClientRuns(clientId: number): Promise<RunSummary[]> {
  return request<RunSummary[]>(`/clients/${clientId}/runs`);
}

export function getClientMisReport(clientId: number): Promise<MisReport> {
  return request<MisReport>(`/clients/${clientId}/mis`);
}

export function uploadRun(
  clientId: number,
  period: string,
  file: File,
): Promise<Run> {
  const formData = new FormData();
  formData.append("period", period);
  formData.append("file", file);
  return request<Run>(`/runs/clients/${clientId}`, {
    method: "POST",
    body: formData,
  });
}

export function getRun(runId: number): Promise<Run> {
  return request<Run>(`/runs/${runId}`);
}

export function correctLineItem(
  runId: number,
  lineItemId: number,
  payload: { resulting_code: string; chat_message?: string; corrected_by?: string },
): Promise<Correction> {
  return request<Correction>(`/runs/${runId}/line-items/${lineItemId}/corrections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
