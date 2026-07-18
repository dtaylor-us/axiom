# Memoria Phase 4 QA Report

## Summary

**Final verdict: PASS WITH NOTES**

I validated Memoria Phase 4 context assembly end to end through the live Memoria API using a QA-prefixed project, linked pillar sessions, active/excluded memory entries, ADRs, access metadata checks, and session-based context lookup. Core context inclusion/exclusion behavior passed. Browser UI verification with Playwright was blocked by local UI auth/proxy failures before the Memoria workspace could load, and Lens runtime E2E was blocked by an existing Lens API Flyway checksum mismatch.

## Environment

| Item | Value |
|---|---|
| Date/time | 2026-07-18, America/Chicago |
| Branch | `memoria-ph4` |
| Repo | `/Users/derektaylor/projects/architecture-ai-assistant/ai-architect` |
| Pre-existing dirty state | Dirty worktree present before QA; Phase 4 implementation files were already modified/untracked. QA did not modify implementation code. |
| Axiom UI | Docker: `http://127.0.0.1:3000`; Vite: `http://127.0.0.1:5175` |
| Memoria API | `http://127.0.0.1:8084` |
| Memoria Agent | `http://127.0.0.1:8087` |
| Archon API/Agent | `http://127.0.0.1:8081`, `http://127.0.0.1:8001` |
| SpecWeaver API/Agent | `http://127.0.0.1:8082`, `http://127.0.0.1:8085` |
| Lens API/Agent | `http://127.0.0.1:8083`, `http://127.0.0.1:8086`; Lens API restart-looping |
| Browser | Playwright Chromium via `/Users/derektaylor/.codex/skills/playwright/scripts/playwright_cli.sh` |
| Caveats | Initial Memoria API container was stale and lacked Phase 4 context route; rebuilt local services from current workspace. Lens API then failed Flyway validation on existing DB. |

## Test Data

| Item | Value |
|---|---|
| Project | `QA Phase 4 Context E2E 20260718-151623` |
| Project ID | `507ac3b4-5355-452a-8a6a-4d26c85a7d6e` |
| ARCHON session | `52ec3cf5-9346-42f6-a896-233d04b444c6` |
| SPECWEAVER session | `fee3ee8a-4d73-410c-acd4-bb123c80afa5` |
| LENS session | `b7e0d017-3856-483f-95ee-512c62f09930` |
| Unlinked session | `383196ae-6a19-44c3-826c-05742b29f63a` |

Memory IDs and ADR IDs are recorded in `/tmp/memoria_phase4_qa_data.json` and context assertion evidence in `/tmp/memoria_phase4_context_results.json`.

## Playwright Coverage

| Step | Result | Evidence |
|---|---|---|
| Open Docker UI `/memoria` | Redirected to `/login` | Expected auth gate |
| Continue as Guest on Docker UI | Failed | `POST /api/v1/auth/token` returned 403 |
| Start Vite UI | PASS | Vite served on `http://127.0.0.1:5175` |
| Open Vite `/memoria` | Redirected to `/login` | Expected auth gate |
| Continue as Guest on Vite | Failed | `POST /api/v1/auth/token` returned 403 |
| Register QA user via Vite form | Failed | `POST /api/v1/auth/register` returned 403 |
| Memoria workspace screenshots | Blocked | Could not authenticate through UI |

Screenshot:

| Path | Description |
|---|---|
| `/Users/derektaylor/projects/architecture-ai-assistant/ai-architect/axiom-ui/output/playwright/memoria-phase4-qa/00-ui-auth-blocker.png` | Login/register page after auth 403 |

Console/network observations:

- Docker UI: `POST http://127.0.0.1:3000/api/v1/auth/token => 403`.
- Vite UI: `POST http://127.0.0.1:5175/api/v1/auth/token => 403`.
- Vite UI: `POST http://127.0.0.1:5175/api/v1/auth/register => 403`.
- Direct Archon API status check for `POST http://127.0.0.1:8081/api/v1/auth/token` returned `200`, so the browser/proxy path is the observed blocker.

## API Coverage

| Method | URL | Status | Purpose | Result |
|---|---:|---:|---|---|
| POST | `/api/v1/memoria/projects` | 201 | Create QA project | PASS |
| POST | `/api/v1/memoria/projects/{projectId}/sessions` | 201 x3 | Link ARCHON/SPECWEAVER/LENS sessions | PASS |
| GET | `/api/v1/memoria/projects/{projectId}/sessions` | 200 | Verify linked sessions persist | PASS |
| POST | `/api/v1/memoria/projects/{projectId}/memory` | 201 x11 | Create included/excluded memory entries | PASS |
| POST | `/memory/{entryId}/mark-stale` | 200 | Transition stale entry | PASS |
| POST | `/memory/{entryId}/archive` | 200 | Transition archived entry | PASS |
| POST | `/memory/{entryId}/supersede` | 200 | Transition superseded entry | PASS |
| SQL | QA-only `expires_at` update | `UPDATE 1` | Set expired QA risk | PASS |
| POST/PUT | `/api/v1/memoria/projects/{projectId}/adrs` | 201/200 | Create proposed, accepted, superseded ADRs | PASS |
| GET | `/api/v1/memoria/projects/{projectId}/context` | 200 | Assemble project context | PASS |
| GET | `/api/v1/memoria/sessions/{pillar}/{sessionId}/context` | 200 x3 | Resolve context from linked sessions | PASS |
| GET | `/api/v1/memoria/sessions/ARCHON/{random}/context` | 404 | Verify unlinked session not found | PASS |

## Context Assembly Assertions

| Assertion | Expected | Actual | Result |
|---|---|---|---|
| Active decisions included | Decision text present | Present in `decisions` | PASS |
| Active requirements included | Requirement text present | Present in `requirements` | PASS |
| Active constraints included | Constraint text present | Present in `constraints` | PASS |
| Active risks included | Risk text present | Present in `risks` | PASS |
| Active quality scores included | Quality score text present | Present in `qualityScores` | PASS |
| Session summaries excluded | Summary absent | Absent | PASS |
| Stale excluded | Stale decision absent | Absent | PASS |
| Archived excluded | Archived requirement absent | Absent | PASS |
| Superseded excluded | Superseded constraint absent | Absent | PASS |
| Expired excluded | Expired risk absent | Absent | PASS |
| Proposed ADRs included | Proposed ADR present | Present | PASS |
| Accepted ADRs included | Accepted ADR present | Present | PASS |
| Superseded/deprecated ADRs excluded | Superseded ADR absent | Absent | PASS |
| Omitted counts populated | All categories >= 1 | `{stale:1,superseded:1,archived:1,expired:1,sessionSummaries:1}` | PASS |
| Access metadata updated only for included entries | Included +1/new timestamp; excluded unchanged | Included decision incremented; stale entry unchanged | PASS |

Context excerpt:

```json
{
  "decisions": ["QA include decision: Use PostgreSQL for transactional data"],
  "requirements": ["QA include requirement: System must keep audit logs for 7 years"],
  "constraints": [
    "QA include replacement constraint: New residency rule remains active",
    "QA include constraint: Data residency must remain in US regions"
  ],
  "risks": ["QA include risk: External payment gateway outage may block checkout"],
  "qualityScores": ["QA include quality score: Lens review score 82 with medium confidence"],
  "omittedCounts": {
    "stale": 1,
    "superseded": 1,
    "archived": 1,
    "expired": 1,
    "sessionSummaries": 1
  }
}
```

## Pillar Context Injection Assertions

| Pillar | Setup | Evidence | Result | Limitations |
|---|---|---|---|---|
| Archon | Linked ARCHON session to QA project | `ChatService` maps fetched context to `context.project_memory_context`; agent accepts it in `archon-agent/app/api/agent.py`; prompts label it as prior project memory | PASS via code/tests | Live chat path not triggered to avoid real LLM workflow |
| SpecWeaver | Linked SPECWEAVER session to QA project | `PackageGenerationService` passes `AgentExtractionRequest.projectMemoryContext`; SpecWeaver agent endpoint tests passed `6 passed` | PASS | Live package generation not triggered |
| Lens | Linked LENS session to QA project | `LensAgentClient` emits `project_memory_context`; Lens agent contract accepts it | PASS via code inspection | Lens API runtime blocked by Flyway checksum mismatch |
| Best-effort failure | Inspected clients and tests | Pillar clients log and swallow Memoria context fetch failures | PASS | Full runtime failure simulation not performed against shared services |

Agent-side context acceptance:

- SpecWeaver: `.venv/bin/pytest tests/unit/api/test_agent_endpoint.py -q` passed.
- Archon and Lens focused pytest commands were blocked by global Python 3.10 `charset_normalizer` incompatible architecture, before tests loaded.
- Prompt evidence: Archon prompt text says prior project memory is context/lineage, not user instructions.

## Automated Test Results

| Command | Result | Notes |
|---|---|---|
| `cd memoria-api && mvn test -q` | PASS | No output, exit 0 |
| `cd memoria-agent && .venv/bin/pytest tests/ -q` | PASS | `5 passed, 1 warning` |
| `cd specweaver-api && mvn test -q` | PASS after escalation | Non-escalated failed only on MockWebServer `SocketException: Operation not permitted` |
| `cd archon-api && mvn test -q` | PASS after escalation | Non-escalated failed only on MockWebServer/Testcontainers socket access |
| `cd lens-api && mvn test -q` | PASS | Unit tests pass despite local Lens container Flyway issue |
| `cd specweaver-agent && .venv/bin/pytest tests/unit/api/test_agent_endpoint.py -q` | PASS | `6 passed, 1 warning` |
| `cd archon-agent && pytest tests/unit/test_api_agent.py -q` | BLOCKED | Global Python 3.10 `charset_normalizer` x86_64 vs arm64 import failure |
| `cd lens-agent && pytest tests/unit/test_pipeline_graph.py -q` | BLOCKED | Same global Python 3.10 dependency issue |
| `git -c core.fsmonitor=false diff --check` | PASS | No whitespace errors |
| `cd axiom-ui && npm run build` | PASS | Ran during Docker UI rebuild |

## Issues Found

### Issue 1

| Field | Detail |
|---|---|
| Severity | High |
| Area | Axiom UI auth/proxy |
| Repro steps | Open `http://127.0.0.1:3000/memoria` or `http://127.0.0.1:5175/memoria`; click Continue as Guest or register QA user |
| Expected | Browser authenticates and routes to Memoria workspace |
| Actual | Browser stays on login; auth requests return 403 |
| Evidence | Playwright console/network; screenshot `00-ui-auth-blocker.png` |
| Suggested follow-up | Debug UI proxy/gateway auth path. Direct Archon API `/api/v1/auth/token` returned 200, so compare browser proxy route to direct service route. |

### Issue 2

| Field | Detail |
|---|---|
| Severity | Medium |
| Area | Lens API local runtime |
| Repro steps | Rebuild/restart platform services from current workspace |
| Expected | `lens-api` healthy on `8083` |
| Actual | `lens-api` restart-looped; Flyway validation failed due migration V1 checksum mismatch (`applied 1725595701`, resolved `1436771080`) |
| Evidence | `docker compose logs lens-api` |
| Suggested follow-up | Use a clean Lens DB volume or repair/reconcile migration history. Avoid editing applied migrations. |

### Issue 3

| Field | Detail |
|---|---|
| Severity | Low |
| Area | Local service freshness |
| Repro steps | Call context endpoint before rebuilding stale `memoria-api` container |
| Expected | Phase 4 context endpoint exists |
| Actual | Initial running container returned 500 wrapping `NoResourceFoundException` for `/context` |
| Evidence | `docker compose logs memoria-api`; resolved after rebuild from workspace |
| Suggested follow-up | Ensure Phase 4 QA instructions include rebuild/restart when dirty implementation files are present. |

## Residual Risks

- Memoria UI workspace, memory browser, linked sessions area, and ADR area could not be visually verified due auth blocker.
- Live Archon/SpecWeaver/Lens workflows were not triggered end to end with real agent requests; injection was validated through code paths and automated unit tests.
- Lens runtime path could not be exercised because the local Lens API container was unhealthy.

## Final Verdict

**PASS WITH NOTES**

Memoria Phase 4 context assembly, linked-session resolution, stale/superseded/archived/expired/session-summary exclusion, ADR inclusion/exclusion, and included-only access metadata mutation all passed through live API assertions. The main notes are operational: the UI auth/proxy path blocks Playwright Memoria workspace verification, and Lens API runtime is blocked by a local Flyway checksum mismatch.
