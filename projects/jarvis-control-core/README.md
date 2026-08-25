# JARVIS Control Core v0.13

Deterministic coordination for multiple AI workers. This is infrastructure for JARVIS, not a chatbot UI.

Implemented: value-weighted task priority, capability-aware routing, dependency gates, leased claims, lease recovery/heartbeats, human approval gates, idempotent ingestion, bounded retries, evidence-gated completion, native CLI worker boundaries, PostgreSQL transactional state for multi-machine coordination, persistent memory, scheduling, evaluation infrastructure, deterministic tool permissions, and tamper-evident tool auditing.

## v0.13 — tamper-evident tool audit

JARVIS now records autonomous tool decisions and executions in a SHA-256 hash chain. Every audit row commits to the previous row and its own canonical payload, allowing the verifier to detect historical mutation, insertion/deletion in the middle, or reordering.

High-value security properties:

- `AuditChain` provides hash-chained append-only audit events.
- HMAC checkpoints can anchor the current chain head outside the worker's writable log, exposing tail truncation as well as in-place edits.
- `AuditedGuardedTool` integrates the existing policy boundary with the audit chain.
- Blocked actions, approval requests, consumed approvals, successful tool executions, and tool failures are recorded.
- Audit writes are flushed with `fsync` before acknowledgement.
- The adversarial test suite deliberately mutates actor identity, event content, order, middle entries, and the file tail.

Threat-model limitation: a process that can rewrite both the audit log and every trusted external checkpoint can still forge history. Checkpoint secrets/anchors therefore belong outside the autonomous worker's writable workspace.

Run tests: `PYTHONPATH=. python -m unittest discover -s tests -v`

Local v0.13 validation: 10/10 new adversarial audit tests passed before publication.

## v0.6 — transactional shared state

The previous filesystem lock was safe only for workers sharing one host. v0.6 added:

- `migrations/001_postgres_state.sql` with a durable task/audit schema.
- Atomic `jarvis_claim_next(...)` using `FOR UPDATE SKIP LOCKED` so concurrent workers cannot claim the same task.
- Capability, dependency, lease, retry and approval checks executed inside PostgreSQL.
- DB-side heartbeat, fail/retry and evidence-gated completion functions.
- Partial unique idempotency protection for active tasks.
- `PostgresTaskStore`, a thin Python client that leaves concurrency correctness in the database rather than in each model process.

## Deployment status

The transactional migration is implemented and published, but the configured Supabase project timed out during prior deployment attempts, so live multi-host deployment is not claimed. The next verification milestone remains applying the migration to the JARVIS Supabase/Postgres project, then moving remote audit checkpoints into a trusted external store.
