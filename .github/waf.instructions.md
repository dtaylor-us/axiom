---
applyTo: "**"
---

# Well-Architected Framework — Agent Instructions for Archon

These instructions extend `copilot-instructions.md` and apply to every code
generation or modification task in this repository. They map the five WAF
pillars to the concrete constraints of the Archon codebase.

When a suggestion conflicts with any rule in this file or in `ARCHITECTURE.md`,
do not make it. Explain the violation and offer a compliant alternative.

---

## PILLAR 1 — RELIABILITY

Archon treats pipeline durability as a first-class concern. Every change
that touches the pipeline, SSE layer, or run lifecycle must preserve the
following guarantees.

### 1.1 — Pipeline runs are durable entities, not transient streams

- `PipelineRunService` MUST create a `pipeline_runs` record **before** the
  agent stream begins. A run that has no database record is invisible to
  reconnecting clients.
- Every SSE event MUST be written to `pipeline_events` before it is
  forwarded to the `SseEmitter`. Event persistence is not optional.
- A run with `status = RUNNING` after the stream closes represents an
  interrupted run. Do NOT mark it `COMPLETED` without a corresponding
  `COMPLETE` event.
- When generating reconnect or replay logic, always replay from
  `pipeline_events` — never from an in-memory buffer.

### 1.2 — Timeouts must accommodate re-iteration

- `SseEmitter` timeout MUST be ≥ 600 seconds. Never reduce it.
- `AgentHttpClient` WebClient timeout MUST match the `SseEmitter` timeout.
  A mismatch causes silent truncation of re-iteration runs.
- Do not add `@Timeout` annotations or reactive timeout operators on the
  streaming path without verifying they respect the 600-second budget.

### 1.3 — SSE keepalive must interleave with stage execution

- The pipeline MUST emit `": heartbeat"` SSE comment lines every 15 seconds
  during any long-running stage.
- Keepalive emission MUST NOT wait for the stage to complete. Use
  `asyncio.create_task()` or a background coroutine, not `asyncio.sleep()`
  after the stage result.
- When adding new long-running stages, add keepalive coverage at the same
  time — never defer it.

### 1.4 — Stage fault tolerance: core vs. supporting

- `CORE_STAGES = {requirement_parsing, requirement_challenge,
  characteristic_inference, architecture_generation}`. A failure in a core
  stage MUST emit `ERROR` and halt the pipeline immediately.
- All other stages are supporting. A `ToolExecutionException` in a
  supporting stage MUST:
  1. Record the gap in `context.pipeline_gaps`.
  2. Set `context.has_gaps = True`.
  3. Emit `STAGE_COMPLETE` with `status="completed_with_gaps"`.
  4. Allow the pipeline to continue.
- Never convert a supporting-stage failure into a core-stage halt.

### 1.5 — Re-iteration is bounded

- The pipeline MAY reiterate at most **2 times** (`MAX_ITERATIONS = 2`).
- If `ReviewAgent.should_reiterate = True` but `iteration >= 2`, emit
  `COMPLETE` regardless of the governance score. Do not loop indefinitely.
- The `iteration` counter MUST be incremented **before** the recursive
  pipeline call. Forgetting this produces an infinite loop.
- Always emit a `RE_ITERATE` event before restarting the pipeline so the
  UI and event log reflect the decision.

### 1.6 — Ordering invariant: weakness before FMEA

- `weakness_analyzer` MUST complete before `fmea_analyzer` begins.
- Never use `asyncio.gather()` for `weakness_and_fmea_node`.
- FMEA quality depends on a populated weakness inventory. Parallel
  execution silently degrades output without raising an error.

---

## PILLAR 2 — SECURITY

Every code change must be evaluated against the security rules below in
addition to the OWASP Top 10. Archon handles JWTs, password reset tokens,
and inter-service authentication — each has specific hardening requirements.

### 2.1 — Secret prohibition (ADL-019, Hard)

- MUST NOT hardcode secrets, API keys, or tokens anywhere in source code.
- `INTERNAL_SECRET` and `OPENAI_API_KEY` MUST be read from environment
  variables only.
- When generating configuration, use `${ENV_VAR_NAME}` placeholders and
  note which secret must be injected at runtime.
- The Semgrep rule in `fitness/adl-019-secret-prohibition.yml` enforces this
  in CI. Any pattern that would trigger it is a build failure.

### 2.2 — JWT storage (ADL-023, Hard)

- JWTs MUST be held in Zustand in-memory state only.
- MUST NOT write JWTs to `localStorage`, `sessionStorage`, `IndexedDB`,
  or any persistent browser store.
- When generating auth flows or token refresh logic, confirm the token
  stays exclusively in the Zustand store.

### 2.3 — Password reset token security (ADL-059, Hard)

- Tokens MUST be generated with `java.security.SecureRandom` with a
  minimum of **32 bytes** of entropy.
- Only the **bcrypt hash** of the token is stored in the database. The raw
  token exists only in the email link. Never store the raw token.
- Tokens expire after `TOKEN_EXPIRY_MINUTES = 30` and are single-use
  (`used_at` marked on consumption).
- `POST /api/v1/auth/forgot-password` MUST return HTTP 200 with an
  identical response regardless of whether the email is registered
  (prevents user enumeration — OWASP A07).
- Rate limit reset requests to `MAX_REQUESTS_PER_HOUR = 3` per email per
  hour. Never remove this limit.
- New passwords MUST be at least 12 characters and MUST NOT match the
  current password.

### 2.4 — Inter-service authentication

- `AgentHttpClient` MUST set the `X-Internal-Secret` header on every
  request to `archon-agent`. A missing header MUST result in HTTP 401
  from the agent.
- MUST NOT expose internal exceptions to API consumers. Catch
  `AgentCommunicationException` and map it to a safe, generic error
  response before it reaches the controller.
- MUST validate all incoming requests with `@Valid` on every `@RequestBody`
  and enforce `@NotBlank` / `@Size` constraints on `ChatRequest.message`.

### 2.5 — HTTPS enforcement (ADL-033, Hard)

- The ingress MUST terminate TLS. Any configuration that allows HTTP traffic
  to reach the application tier without TLS is a hard violation.
- When modifying Helm values, Terraform modules, or nginx configuration,
  confirm that TLS termination is preserved.

### 2.6 — LLM prompt injection

- Do not embed user-supplied text directly into prompt templates without
  sanitisation. User input MUST flow through defined Pydantic input models;
  it MUST NOT be concatenated into Jinja2 template strings at runtime.
- Prompt templates live in `app/prompts/` as `.j2` files. Input variables
  are injected via the Jinja2 rendering context, not string concatenation.

---

## PILLAR 3 — COST OPTIMIZATION

LLM API calls are the dominant cost driver in Archon. Every generation that
touches the pipeline, LLM client, or prompt templates must preserve the
token-budget controls below.

### 3.1 — Conversation history is bounded

- `getRecentMessages()` MUST be called with `limit ≤ 20` before building
  `AgentRequest`. Sending full conversation history to the LLM grows
  unboundedly with session length.
- When adding history-retrieval logic, never use an unbounded query.
  The 20-message constant is enforced with an inline comment explaining the
  token-budget rationale (RULE Q-5).

### 3.2 — One LLM call per diagram type

- `DiagramGeneratorTool` MUST call `_generate_single_diagram` once per
  selected diagram type. A single batch call for all types is prohibited
  (ADL assertion `diagram_generation_per_type`).
- Diagram counts are bounded: minimum 3, maximum 5 per pipeline run.
  Generating fewer wastes the analysis; generating more wastes tokens.
- `c4_container`, `sequence_primary`, and `sequence_error` are mandatory
  regardless of style. Do not remove them.

### 3.3 — Structured output reduces repair calls

- Every tool that calls `llm_client.complete()` with `response_format="json"`
  MUST also pass `output_schema` and `schema_name` from
  `app.llm.schemas.SCHEMAS`.
- Schema-enforced calls reduce parse failures, which in turn reduce the
  one-repair-per-stage retry cost. Adding a stage without a schema
  increases expected token spend per run.
- When adding a new stage, add its schema to `SCHEMAS` in the same commit.

### 3.4 — Repair is bounded to one attempt

- `BaseTool.attempt_repair()` MUST be called at most **once** per stage
  failure. If the repair call itself fails, raise `ToolExecutionException`
  immediately — no second repair.
- When writing tool implementations, do not add additional retry loops
  outside of the single-repair contract. Each extra attempt multiplies
  per-run cost.

### 3.5 — Idempotency prevents duplicate pipeline runs (ADL-064, Hard)

- The UI MUST generate an idempotency key on pipeline submission, and the
  API MUST deduplicate requests sharing the same key. A missing key allows
  double-clicks or network retries to trigger multiple billable pipeline runs.
- When modifying the submission path in `ChatController` or the SSE fetch
  hook, confirm the idempotency key is present and validated.

---

## PILLAR 4 — OPERATIONAL EXCELLENCE

Archon's observability model is built on structured SSE events and fitness
functions. Every operational change must maintain the event contract and
ADL conformance.

### 4.1 — Stage event contract (ADL-018, Soft)

- Every pipeline stage MUST emit `STAGE_START` before any work begins and
  `STAGE_COMPLETE` after the stage finishes. No exceptions.
- `STAGE_COMPLETE` for a supporting stage that caught a
  `ToolExecutionException` MUST include `status="completed_with_gaps"`.
- The `COMPLETE` event MUST include `has_gaps` and `pipeline_gaps` fields
  so clients and log aggregators can distinguish clean runs from partial runs.
- When adding a pipeline stage, add both event emissions in the same commit
  as the node implementation. Defer neither.

### 4.2 — Error events must be emitted before the stream closes

- Every unhandled exception in the pipeline MUST yield a final `ERROR`
  chunk before the coroutine returns. A silent stream termination leaves
  the run in `RUNNING` state indefinitely.
- Do not use bare `except:` — catch specific exception types and include
  enough context (stage name, iteration) in the error payload to diagnose
  the failure without a debugger.

### 4.3 — Governance score visibility

- `review_health_visible` asserts that a governance score with failed
  sub-reviews is distinguishable from one with all sub-reviews passing.
- `governance_score_confidence` MUST be `high` / `partial` / `low` /
  `unavailable` based on sub-review success count. Do not default to `high`.
- The UI MUST display a degradation warning when `review_completed_fully`
  is `false`. Do not remove this warning without updating the assert.

### 4.4 — Pipeline gap visibility in the UI

- The UI MUST display an amber indicator on any stage whose
  `STAGE_COMPLETE` payload carries `status="completed_with_gaps"`.
- The UI MUST display a banner when the `COMPLETE` event has `has_gaps=true`.
- This visibility is what makes supporting-stage resilience useful in
  production. Without it, users cannot tell whether gaps occurred.

### 4.5 — Fitness functions must stay green

- The `fitness/` directory contains executable ADL conformance scripts.
  Run `fitness/run-all.sh` after any structural change to service
  boundaries, module layout, or security-sensitive code paths.
- Hard-enforcement ADL violations (ADL-004, 005, 007, 013, 014, 019, 023,
  024, 025, 026, 027, 028, 033, 034, 059) MUST cause `run-all.sh` to exit
  non-zero. Do not suppress these.
- When adding a new ADL rule, add a corresponding fitness function script
  in the same commit and register it in `run-all.sh`.

### 4.6 — New pipeline stages require atomic updates

When adding a pipeline stage, update **all** of the following in a single
commit. A partial update breaks tests in a different layer.

| File | What to update |
|------|----------------|
| `archon-agent/app/pipeline/graph.py` | Add stage name to `ORDERED_STAGES` |
| `archon-agent/app/pipeline/nodes.py` | Implement the stage node function |
| `archon-agent/app/tools/registry.py` | Register the tool |
| `axiom-ui/src/types/api.ts` | Add stage name to `PIPELINE_STAGES` |
| `axiom-ui/src/components/StageProgress.tsx` | Add label to `STAGE_LABELS` |
| `archon-agent/app/llm/schemas.py` | Add output schema to `SCHEMAS` |
| `ARCHITECTURE.md` | Document the stage under PIPELINE DEFINITION |
| `ADL.md` | Update service index if a new ADL rule is added |
| `tests/unit/test_pipeline_reiteration.py` | Update `len(ORDERED_STAGES)` assertion |
| `tests/unit/test_pipeline_nodes.py` | Add mock and test for the new node |
| `axiom-ui/src/test/StageProgress.test.tsx` | Update stage count assertion |
| `axiom-ui/src/test/useConversation.test.ts` | Update stage count assertion |

The stage name MUST be identical (exact `snake_case`) in every location.

### 4.7 — ArchitectureContext field additions

- Every new `ArchitectureContext` field MUST have a default value.
  A field without a default breaks any test that constructs the model
  explicitly, and breaks deserialization of runs in progress during a
  rolling deploy.
- Every new field MUST include an inline comment naming the stage that
  populates it.

---

## PILLAR 5 — PERFORMANCE EFFICIENCY

Archon's performance model depends on non-blocking I/O, async parallelism,
and token-efficient LLM interactions. Never introduce blocking patterns on
the SSE streaming path.

### 5.1 — Non-blocking HTTP is mandatory in archon-api

- `RestTemplate` is categorically prohibited (ADL-005, Hard). It is
  blocking and will deadlock the SSE response thread under load.
- All HTTP calls from `archon-api` to `archon-agent` MUST use
  `WebClient` with reactive operators (`Flux`, `Mono`).
- Do not add `block()` calls on the streaming path. If a blocking call is
  genuinely required (e.g., during startup), document it with an inline
  comment explaining why it cannot be made reactive.

### 5.2 — Database sessions must not span HTTP responses

- `spring.jpa.open-in-view` MUST be `false`. An open session across the
  SSE streaming response holds a database connection for the full stream
  duration, exhausting the connection pool under load.
- When generating `application.yml` or configuration classes, verify this
  property is absent or explicitly `false`.

### 5.3 — Parallel execution is scoped to safe stages only

- Stages 9 (`adl_generation`) and 10 (`weakness_analysis`) run concurrently
  via `asyncio.gather()`. This is intentional — they write to separate
  `ArchitectureContext` fields.
- `weakness_analyzer` and `fmea_analyzer` MUST NOT run concurrently (see
  Reliability 1.6). The gather in the pipeline graph is for stages 9 and 10
  only.
- When adding a new stage, explicitly decide whether it can run in parallel
  and document the decision with an inline comment in `graph.py`.

### 5.4 — ReadableStream is the only SSE client mechanism

- The UI MUST use `fetch + ReadableStream` to consume the SSE streaming
  endpoint. `EventSource` is prohibited because the endpoint requires a
  POST body.
- When generating streaming hooks or SSE consumers in TypeScript, always
  use the `ReadableStream` + `getReader()` pattern, not `EventSource`.

### 5.5 — API calls are isolated to the api module

- MUST NOT perform `fetch` calls inside React components. All HTTP calls
  live in `src/api/` modules only. This keeps network I/O decoupled from
  render cycles and makes performance profiling tractable.

### 5.6 — Scenario deduplication before the pipeline (ADL-065, Hard)

- Scenario deduplication MUST occur before the pipeline begins, not inside
  a stage. Duplicate scenarios passed to downstream stages inflate token
  consumption in every subsequent LLM call.

---

## WAF CROSS-CUTTING CHECKS

Run these checks before declaring any task complete:

| Concern | Check |
|---------|-------|
| **Secrets** | No literal key, token, or password in source or config |
| **Durability** | New pipeline paths create run records and persist events |
| **Events** | Every stage emits `STAGE_START` and `STAGE_COMPLETE` |
| **Blocking I/O** | No `RestTemplate`, no `block()` on the SSE path, no `open-in-view` |
| **Token budget** | History limited to 20, diagram count 3–5, one repair per stage |
| **ADL conformance** | `fitness/run-all.sh` exits 0 for the modified service |
| **Test coverage** | ≥ 80% line coverage per package; all test suites pass |
| **Default values** | New `ArchitectureContext` fields have defaults |
| **Atomic stage add** | All locations in the stage-addition checklist updated |
