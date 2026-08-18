# JARVIS Control Core v0.6

Deterministic coordination for multiple AI workers. This is infrastructure for JARVIS, not a chatbot UI.

Implemented: value-weighted task priority, capability-aware routing, dependency gates, leased claims, lease recovery/heartbeats, human approval gates, idempotent ingestion, bounded retries, evidence-gated completion, native CLI worker boundaries, append-only audit events, and now a PostgreSQL transactional state layer for multi-machine coordination.

## v0.6 — transactional shared state

The previous filesystem lock was safe only for workers sharing one host. v0.6 adds:

- `migrations/001_postgres_state.sql` with a durable task/audit schema.
- Atomic `jarvis_claim_next(...)` using `FOR UPDATE SKIP LOCKED` so concurrent workers cannot claim the same task.
- Capability, dependency, lease, retry and approval checks executed inside PostgreSQL.
- DB-side heartbeat, fail/retry and evidence-gated completion functions.
- Partial unique idempotency protection for active tasks.
- `PostgresTaskStore`, a thin Python client that leaves concurrency correctness in the database rather than in each model process.

Run tests: `PYTHONPATH=. python -m unittest discover -s tests -v`

Local v0.6 validation includes contract tests plus a 20-thread contention model in which exactly one worker acquires one available task.

## Deployment status

The migration is implemented and published, but the configured Supabase project timed out repeatedly during this build, so **live deployment is not claimed**. The next verification milestone is applying the migration to the JARVIS Supabase/Postgres project and running a real concurrent claim test against that database.
