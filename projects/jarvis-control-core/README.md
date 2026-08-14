# JARVIS Control Core v0.2

Deterministic coordination for multiple AI workers. This is infrastructure for JARVIS, not a chatbot UI.

Implemented: value-weighted task priority, capability-aware routing, dependency gates, exclusive leased claims, lease heartbeats/recovery, human approval gates, idempotent task ingestion, bounded retries, evidence-gated completion, atomic state replacement, and append-only audit events.

Run tests: `PYTHONPATH=. python -m unittest discover -s tests -v`

Validated locally on 2026-08-15: 12/12 regression tests passed.

Limitation: filesystem state/locking is single-host. Before independent Claude/Codex/Gemini machines write concurrently, claims should move to a transactional shared store such as Postgres/Supabase.
