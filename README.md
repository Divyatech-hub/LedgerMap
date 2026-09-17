# LedgerMap

Automates mapping monthly trial balances (Tally, Zoho, QuickBooks, and ERP exports)
to a client's IFRS-coded Detailed MIS template — built for a family accounting
consultancy handling multiple clients across different bookkeeping systems.

## The problem

Each month, for each client, the accountant takes a raw trial balance export and
manually assigns each line item an internal IFRS-aligned code, so it can be
aggregated into that client's Detailed MIS report (P&L + Balance Sheet, broken
out by category). Account names differ by client and by source software, so this
can't be a simple string match — it needs matching against history first, then
fuzzy matching, then LLM classification as a last resort, with a human review
step for anything uncertain.

## Core architecture


### Key design decisions (validated against 3 real client files)

1. **Persistent mapping memory, not per-month re-classification.** Most account
   names repeat month to month. Build one `account_mappings` table per client
   (`raw_name → code`, with confidence/method/history) from historical TB tabs +
   existing MIS files. Check this FIRST, every month — exact match handles the
   large majority for free, before any LLM call is needed.

2. **Source-type fork, checked before anything else.** Not every client has a
   name→code classification problem. Clients on a proper ERP (e.g. an
   Oracle/JDE-class GL export — signature headers like "G/L Period", "Fiscal
   Year", "Trail Balance By Company Division Object") already export reliable
   numeric GL codes on every line. Those clients only need code-based
   aggregation, no classification at all. Clients on free-text ledger software
   (Tally, Zoho, QuickBooks) need the full match/classify pipeline. Detect this
   per file before deciding which path to run.

3. **Chart of accounts is per-client, not shared.** Confirmed by comparing two
   real clients: one uses 4-digit codes (`2001`, `3001`...), another (an ERP
   export) uses 6-digit hierarchical codes (`411001`...) — completely
   unrelated schemes. `account_mappings` and the taxonomy must be siloed per
   client. (Within ONE client that has multiple divisions/branches, the
   taxonomy IS shared across those divisions — the isolation boundary is the
   client/company, not the division.)

4. **Hierarchy-aware TB parsing, not flat row scanning.** Tally/similar TBs are
   indented trees: bold, indent-0 rows are group headers (skip, never
   classify); some branches are sub-ledger detail (AR/AP broken out by
   customer/supplier/project name) that should inherit ONE code from wherever
   that branch actually represents receivables/payables, not be classified
   individually by company name; only genuine leaf GL accounts need
   match/classify. Getting this right took exact-match coverage on one real
   test file from 61% (naive flat parsing) to 83% (hierarchy-aware) with zero
   LLM calls — the classifier should only ever see what's left after this.

5. **LLM classification is constrained, not open-ended.** The target taxonomy
   is a fixed, closed list per client (extracted from their Detailed MIS). The
   classifier must return either a real code from that list or an explicit
   `NONE_MATCH` — never an invented code. Pass the account's ancestor chain in
   the TB hierarchy as context, not just the raw name — for sub-ledger detail
   lines, the name alone (a company name) is meaningless; the position in the
   hierarchy is what tells you it's receivables, not an expense category.

6. **LLM cost is a non-issue at this volume, provider choice shouldn't be
   over-optimized.** With the mapping memory doing most of the work, expect
   well under 500 LLM calls/month across all clients combined — under $1/month
   on any current model (Claude Haiku, Gemini Flash-Lite, Grok, all checked).
   Keep the classifier function provider-agnostic (swap models without
   touching the rest of the pipeline) rather than picking a "cheap" model
   upfront; self-hosting an open-source model is not worth the ops overhead at
   this scale.

7. **Human review/correction closes the loop.** Anything below a confidence
   threshold, or any chat-based correction from the accountant, gets written
   back into `account_mappings` as a human-approved entry — the system should
   get cheaper and more accurate every month per client, never ask about the
   same line twice.

## Product surface (what to build toward)

- Upload a new month's raw TB for a client
- Pipeline runs automatically (or via a "refresh" action)
- **Preview**: the full Detailed MIS (all historical columns + new month)
  rendered as a table, new column's cells color-coded by resolution method
  (exact/fuzzy = confident, LLM/low-confidence = flagged for review)
- **Chat correction**: a chat panel next to the preview — the accountant can
  say "Business Credit Card should be 2069 not 2068" in plain language;
  Claude identifies the specific line item(s), applies the fix live in the
  preview, AND writes it back into `account_mappings` permanently
- **Finalize/export**: writes the real `.xlsx`, new column appended to
  Detailed MIS matching the client's existing template/formulas exactly

## Data model (rough)

- `clients` — one row per client company
- `account_mappings` — `(client_id, raw_name, code, confidence, method, approved_by, last_seen)`
- `runs` — `(client_id, period, status)`
- `run_line_items` — `(run_id, raw_name, amount, matched_code, confidence, method, status)`
- `corrections` — `(run_id, line_item_id, chat_message, resulting_code, timestamp)` — full audit trail (matters a lot for an accounting tool)

## Stack

Given real volume here (one firm, handful of clients, monthly runs) — deliberately
NOT over-engineered:
- Backend: Python (FastAPI), pandas/openpyxl for TB parsing
- Frontend: React, spreadsheet-style preview + chat sidebar
- DB: Postgres (pgvector if embeddings end up useful for the classify shortlist step)
- Deploy: single small service, scales to zero between monthly runs

## What's already prototyped (see /prototype)

Built and validated against three real files from one client + one other
client's ERP export:

- `build_mapping_memory.py` — extracts persistent (name→code) mapping from
  historical TB tabs + existing mapping sheets. Also flags names that got
  inconsistent codes across history (real finding: 11 such cases in the test
  data — worth flagging to the accountant, not silently picking one).
- `extract_taxonomy.py` — pulls the fixed (code→description) taxonomy from a
  client's Detailed MIS, for use as the classifier's closed answer set.
- `detect_source_type.py` — ERP-export vs free-text-ledger detection via
  header fingerprint + code-column shape. Verified correct on both real test
  files.
- `parse_tb_hierarchy.py` — indent-hierarchy-aware parsing: group headers vs
  roll-up sub-ledger detail vs genuine leaf accounts.
- `match_new_tb.py` — exact match then fuzzy match (rapidfuzz) against mapping
  memory.
- `classify_unresolved.py` — LLM classification fallback via Claude, tool-use
  constrained to the fixed taxonomy + `NONE_MATCH`, with hierarchy context in
  the prompt. **Not yet run end-to-end — needs `ANTHROPIC_API_KEY` set; the
  original prototyping environment had no API credentials.**

## Known gaps to fix (real, not hypothetical — found via real data)

- `parse_tb_hierarchy.py`'s roll-up detection uses a hardcoded group-name list
  (`ROLLUP_GROUP_NAMES = {"sundry debtors", "sundry creditors", ...}`). On the
  real test client, receivables are actually grouped by customer/project name
  (e.g. "KAUST"), not a literal "Sundry Debtors" label — so this needs a more
  general heuristic (e.g. depth/position-based: "customer-name-shaped leaves
  past a certain hierarchy depth under Current Assets/Liabilities are
  sub-ledger detail") rather than a name allowlist.
- Two parsing edge cases leak through as false "leaf accounts": a spreadsheet
  footer row (`Grand Total`) and a legitimately-real single account
  (`Cash-in-Hand`) that has no children so it registers as a leaf — needs
  explicit filtering.
- No persistent storage yet — prototype scripts read/write local JSON as a
  stand-in for the `account_mappings` Postgres table described above.
- Only tested against one client's one month, plus header-level inspection of
  a second client's ERP export. Multi-client support (isolated
  `account_mappings` + taxonomy per client, per Key Design Decision #3 above)
  is architecturally accounted for but not implemented.
- LLM classification path is written but unexecuted end-to-end (needs a real
  API key in this environment to validate the actual output quality).

## Security / privacy notes

This handles real client financial data (account names, balances, sometimes
individual names within account labels). Treat accordingly:
- Don't commit real client `.xlsx`/`.xls` files to git — add them to
  `.gitignore`, keep them local or in a private, access-controlled store
- Route all LLM calls through the API (not a consumer chat product) for
  standard 7-day log retention and no training use; ask about a Zero Data
  Retention agreement with Anthropic once this moves from prototype to
  production with live client books
- Full audit trail (the `corrections` table) is a defensibility requirement
  for this domain, not a nice-to-have — every code assignment should be
  traceable to its method and, if overridden, to who overrode it and why