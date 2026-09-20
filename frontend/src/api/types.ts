// Mirrors backend/src/ledgermap/schemas/{clients,runs}.py — keep in sync by hand
// until there's a generated-client step.

export interface Client {
  id: number;
  name: string;
  created_at: string;
}

export interface RunSummary {
  id: number;
  client_id: number;
  period: string;
  status: string;
  source_type: string | null;
  created_at: string;
}

export interface RunLineItem {
  id: number;
  raw_name: string;
  amount: string;
  row_number: number | null;
  ancestors: string[];
  matched_code: string | null;
  confidence: string | null;
  method: string;
  status: string;
  review_reason: string | null;
}

export interface Run {
  id: number;
  client_id: number;
  period: string;
  status: string;
  source_type: string | null;
  original_filename: string | null;
  created_at: string;
  completed_at: string | null;
  total_rows: number;
  resolved_rows: number;
  review_rows: number;
  line_items: RunLineItem[];
}

export interface Correction {
  id: number;
  run_id: number;
  line_item_id: number;
  previous_code: string | null;
  resulting_code: string;
  is_conflict: boolean;
  chat_message: string | null;
  corrected_by: string | null;
  created_at: string;
}

export interface MisCell {
  amount: string;
  method: string;
}

export interface MisRow {
  code: string;
  description: string | null;
  cells: Record<string, MisCell>;
}

export interface MisReport {
  periods: string[];
  rows: MisRow[];
  unresolved_periods: string[];
}

export interface ChatCandidate {
  id: number;
  raw_name: string;
  ancestors: string[];
  matched_code: string | null;
}

export interface ChatCorrectionResponse {
  applied: boolean;
  explanation: string;
  correction: Correction | null;
  candidates: ChatCandidate[];
}

export interface ApiErrorBody {
  detail?: string;
}
