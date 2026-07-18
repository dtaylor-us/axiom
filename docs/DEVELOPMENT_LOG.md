# Memoria Phase 2 Development Log

## Scope

Phase 2 turns Memoria from a foundation scaffold into a manual project-memory workspace. The scope is intentionally non-agentic at runtime: no LLM calls, no automatic distillation, and no context injection into other pillars.

## Engineering Guardrails

- Preserve ADL-100: memory entries are never physically deleted.
- Keep memoria-api free of LLM dependencies and calls.
- Keep memoria-agent free of database access.
- Treat supersession and stale/archive states as explicit lifecycle transitions.
- Prefer backend summary/query contracts over duplicating business logic in the UI.
- Keep UI workflows operational and dense: project memory work should be the first screen.

## Implementation Plan

1. Add query/filter support for memory entries and ADRs.
2. Add manual memory lifecycle actions: mark stale, archive, restore, supersede.
3. Add promote-to-ADR and ADR supersession support.
4. Add project memory summary endpoint for UI dashboards.
5. Add Flyway migration for Phase 2 indexes and ADR source-memory lineage.
6. Add Memoria API client and UI workspace in axiom-ui.
7. Extend pillar navigation/icon/routing to include Memoria.
8. Add focused service/UI tests and run verification.

## Work Notes

- 2026-07-18: Phase 1 scaffold found in repo for memoria-api and memoria-agent. Existing API includes basic project/session/memory/ADR CRUD and service tests.
- 2026-07-18: Phase 2 implementation started with backend contracts first so the UI can stay thin and deterministic.
- 2026-07-18: Added Phase 2 backend contracts:
  - Filtered memory browsing by status, type, tier, source pillar, tag, date, expiry, and text.
  - Manual lifecycle endpoints for mark stale, archive, restore, supersede, and promote to ADR.
  - Filtered ADR browsing and ADR supersession.
  - Project memory summary endpoint for dashboard counts.
  - ADR source-memory lineage via `source_memory_entry_id`.
- 2026-07-18: Added Flyway V5 for Phase 2 indexes and ADR lineage.
- 2026-07-18: Added focused service tests for lifecycle transitions, filtering, promotion lineage, project summary counts, and ADR supersession.
- 2026-07-18: Added `axiom-ui` Memoria API client, local Vite proxy, pillar icon/badge/nav support, and `/memoria` route.
- 2026-07-18: Added a single Memoria workspace page with project creation, linked session management, health summary, knowledge browser, manual memory entry creation, memory lifecycle actions, ADR creation, promotion, and ADR supersession.
- 2026-07-18: Kept memoria-agent unchanged except for verification; Phase 2 still has no runtime LLM calls, no automatic distillation, and no context injection.
- 2026-07-18: Adjusted Memoria project header identity resolution to tolerate non-UUID local UI identities by mapping them to deterministic UUIDs, matching the existing authentication resolver behavior.
- 2026-07-18: Fixed local Docker development wiring discovered from browser console 502s:
  - Added `MEMORIA_API_PROXY_TARGET=http://memoria-api:8084` to `docker-compose.override.yml` so Vite-in-Docker proxies `/memoria-api` to the Memoria API container instead of container-local localhost.
  - Added a `/memoria-api/` compatibility route to `axiom-ui/nginx.conf` for production-style Docker UI serving.
  - Added `JWT_SECRET` to the Memoria API compose environment so the service can start in local Docker.
  - Switched local Postgres to `pgvector/pgvector:pg16`, preserving the existing volume, because Memoria migrations require the `vector` extension.
  - Added `docker/postgres-init/02-create-memoria-db.sql` for fresh local volumes.
  - Created the `memoria` database manually in the existing local volume because init scripts do not run against an already-initialized Postgres data directory.
- 2026-07-18: Fixed local Memoria navigation logout/session-expired behavior:
  - Root cause: local Memoria requests were returning `401`, and the shared UI HTTP helper treats any `401` as a global expired-session signal.
  - Added Memoria security coverage for stale local bearer tokens.
  - Changed the Memoria UI client to avoid sending Archon bearer tokens through the local `/memoria-api` proxy path.
  - Disabled the Memoria API internal-secret requirement in local compose so `X-Axiom-User-Id` identity headers are accepted during local development.
  - Rebuilt and restarted `memoria-api` after the auth/proxy fixes.

## Current Local Development State

- `postgres` runs with `pgvector/pgvector:pg16` so Memoria's `vector` migration succeeds.
- `memoria-api` is reachable on port `8084`.
- `memoria-agent` is reachable on port `8087`.
- The in-app browser/Vite path for Memoria is `http://127.0.0.1:5173/memoria`.
- The Docker UI path for Memoria is `http://localhost:3000/memoria`.
- Local `/memoria-api` requests rely on `X-Axiom-User-Id` rather than the Archon bearer token to avoid false global session-expired events.

## Verification Log

- PASS: `cd memoria-api && mvn compile -q`
- PASS: `cd memoria-api && mvn test -q`
- PASS: `cd axiom-ui && npm run build`
- PASS: `cd memoria-agent && .venv/bin/pytest tests/ -q`
- PASS: `docker compose --profile memoria config --services` includes `memoria-agent` and `memoria-api`.
- PASS: ADL-100 grep found no `.delete(` or `.deleteById(` calls in `MemoryEntryService.java`.
- NOTE: Plain system `pytest` initially failed before collection because a global pytest plugin loaded an incompatible `charset_normalizer` binary. The service `.venv` run passed.
- PASS: `curl http://127.0.0.1:8084/actuator/health` returns `{"status":"UP"}` from local Docker.
- PASS: `curl http://localhost:3000/memoria-api/api/v1/memoria/projects` returns `200 []` through the Docker Vite proxy.
- PASS: `curl -H 'X-Axiom-User-Id: guest' http://127.0.0.1:5173/memoria-api/api/v1/memoria/projects` returns `200 []` through the in-app browser/Vite path.
- PASS: `docker compose --profile memoria ps memoria-api ui postgres memoria-agent` shows Memoria API, Memoria agent, Postgres, and UI running; Memoria API/agent/Postgres are healthy.

# Memoria Phase 3 Development Log

## Scope

Phase 3 turns Memoria from manual project memory into automatic post-session distillation. The implemented scope covers automatic candidate extraction, conflict/supersession detection, Memoria-owned persistence, and best-effort session-completion notifications from SpecWeaver, Archon, and Lens.

Context injection into new pillar sessions remains out of scope for this commit. Embedding generation also remains out of scope at runtime; the current Phase 3 path is deterministic and testable without an LLM or external embedding provider.

## Engineering Guardrails

- Preserve ADL-100: memory entries are never physically deleted.
- Keep `memoria-agent` free of database access. It reasons over request payloads and returns candidates/conflicts only.
- Keep `memoria-api` as the only writer of memory lifecycle state.
- Keep distillation best-effort from source pillars: a Memoria outage must not fail package generation, architecture generation, or Lens review completion.
- Prefer explicit source lineage: all generated entries carry `sourcePillar`, `sourceSessionId`, and agent-provided `sourceExcerpt`.
- Make automatic supersession conservative: a conflict flag only supersedes an existing entry after the replacement entry has been created successfully.
- Avoid hard LLM dependency for the first Phase 3 implementation so local CI and dev machines can verify behavior without secrets.

## Implementation Plan

1. Replace the `memoria-agent` `/distill` stub with a real pipeline.
2. Add deterministic fact extraction from structured payloads and labelled text.
3. Add deterministic conflict/supersession detection against active existing memory.
4. Add a Memoria API distillation orchestrator that resolves linked sessions, calls the agent, writes candidates, and applies supersession.
5. Add internal Memoria API endpoints for direct and linked-session distillation.
6. Add best-effort session-completion notification clients in SpecWeaver, Archon, and Lens.
7. Add focused tests for agent extraction/conflict behavior and API orchestration.
8. Verify central Memoria services and touched pillar services.

## Work Notes

- 2026-07-18: Replaced the Phase 1 `memoria-agent` distiller stub with an automatic pipeline:
  - `fact_extractor.py` now extracts `DECISION`, `REQUIREMENT`, `RISK`, `QUALITY_SCORE`, `ASSUMPTION`, `CONSTRAINT`, and `SESSION_SUMMARY` candidates.
  - Extraction supports structured payload fields such as `decisions`, `requirements`, `risks`, `fmea_risks`, `quality_scores`, `assumptions`, and `constraints`.
  - Extraction also supports labelled prose such as `Decision: ...`, `Requirement: ...`, and `Risk: ...`.
  - Explicit labels now win over generic keywords; for example `Requirement: Use ...` remains a requirement even though it contains the word `Use`.
  - Session summaries are captured as `SESSION_SUMMARY` entries for lineage, preserving the Phase 2 rule that summaries should not become context-injected facts.
- 2026-07-18: Added `conflict_detector.py` implementation:
  - Compares new candidates with active existing entries supplied by `memoria-api`.
  - Requires matching memory type before conflict consideration.
  - Flags replacement-style language such as `instead of`, `replaces`, `supersedes`, `no longer`, and `rather than`.
  - Also detects high-overlap same-tag facts as likely replacements.
  - Emits `ConflictFlag` records with `existing_entry_id`, `new_candidate_index`, `conflict_description`, and `supersedes`.
- 2026-07-18: Extended `memoria-agent` contracts:
  - `DistillRequest` now accepts `session_payload`.
  - `ConflictFlag` now includes a `supersedes` boolean.
  - `/distill` now returns a real candidate/conflict response message instead of the old empty stub message.
- 2026-07-18: Added Memoria API agent contract DTOs:
  - `AgentDistillRequest`
  - `AgentDistillResponse`
  - `AgentMemoryCandidate`
  - `AgentConflictFlag`
  - JSON property annotations bridge Spring camelCase records to FastAPI snake_case fields.
- 2026-07-18: Added Memoria API orchestration:
  - `MemoriaAgentConfig` binds `memoria.agent.base-url`, `memoria.agent.internal-secret`, and timeout settings.
  - `MemoriaAgentClient` calls `memoria-agent /distill` with `X-Internal-Secret`.
  - `DistillationService` resolves project context either from an explicit `projectId` or from `project_session_links` using `(pillar, sessionId)`.
  - The service sends only ACTIVE existing entries to the agent.
  - Duplicate protection skips candidate creation when the same source pillar/session/content already exists.
  - The service writes new entries through `MemoryEntryService.createEntry`, preserving TTL assignment and lifecycle rules.
  - Supersession uses `MemoryEntryService.supersede` after a replacement entry is created, preserving no-delete lineage.
  - Bad or stale conflict references from the agent are ignored without failing valid candidate creation.
- 2026-07-18: Added Memoria API distillation endpoints:
  - `POST /api/v1/memoria/distill-session` for explicit project-aware distillation.
  - `POST /api/v1/memoria/sessions/{pillar}/{sessionId}/distill` for linked-session distillation from source pillars.
- 2026-07-18: Added SpecWeaver completion notification:
  - New `MemoriaNotificationClient` posts to linked-session distillation after package generation reaches `PACKAGE_READY`.
  - Uses generated brief text as `sessionSummary`.
  - Parses the Arch input package JSON into `sessionPayload`, falling back to raw `package_json` if parsing fails.
  - Failures are logged and swallowed so SpecWeaver package generation remains successful.
- 2026-07-18: Added Lens completion notification:
  - New `MemoriaNotificationClient` posts after the review report is saved and the review session transitions to `COMPLETE`.
  - Uses the executive summary as `sessionSummary`.
  - Sends the persisted `ReviewReport` converted to a map as `sessionPayload`.
  - Failures are logged and swallowed so Lens review completion remains successful.
- 2026-07-18: Added Archon completion notification:
  - New `MemoriaNotificationClient` posts from the existing post-stream persistence block after structured outputs/token usage are handled.
  - Uses the assistant text buffer as `sessionSummary`.
  - Sends the `structured_output` map as `sessionPayload`.
  - Failures are logged and swallowed so Archon stream completion remains successful.
- 2026-07-18: Added focused tests:
  - `memoria-agent/tests/unit/test_distiller.py` covers structured candidate extraction and replacement conflict flags.
  - `memoria-agent/tests/conftest.py` ensures tests import the local source tree rather than a stale installed egg.
  - Updated the existing Memoria agent health/distill test from Phase 1 empty-stub expectations to Phase 3 pipeline expectations.
  - `DistillationServiceTest` covers linked-project resolution, candidate creation, confidence/type mapping, and supersession after replacement creation.
  - Updated existing SpecWeaver and Archon tests for the new notification client constructor dependencies.

## Current Local Development State

- `memoria-agent /distill` is active and deterministic.
- `memoria-api` owns all Phase 3 memory writes and lifecycle changes.
- Source pillars can notify Memoria by session ID; the session must already be linked to a Memoria project.
- If no project link exists, Memoria returns `ResourceNotFoundException`; the source pillar clients catch/log the failure and continue.
- `MEMORIA_API_BASE_URL`, `MEMORIA_API_TIMEOUT_SECONDS`, and `MEMORIA_NOTIFICATIONS_ENABLED` configure pillar-to-Memoria notifications.
- `MEMORIA_AGENT_BASE_URL`, `MEMORIA_AGENT_INTERNAL_SECRET`, and `AGENT_TIMEOUT_SECONDS` configure Memoria API-to-agent calls.

## Verification Log

- PASS: `cd memoria-agent && .venv/bin/pytest tests/ -q`
- PASS: `cd memoria-api && mvn test -q`
- PASS: `cd lens-api && mvn test -q`
- PASS: `cd specweaver-api && mvn test -q` with escalation because MockWebServer tests need local socket binding.
- PASS: `cd archon-api && mvn test -q` with escalation because MockWebServer/Testcontainers probes need local socket/Docker access.
- NOTE: Non-escalated `specweaver-api` and `archon-api` test runs failed only on sandbox `SocketException: Operation not permitted` from MockWebServer local port binding.
- NOTE: SpecWeaver PDFBox/font warnings appeared during tests and are pre-existing expected negative-path/test-environment noise; the escalated test run passed.
