# Axiom — Architecture Intelligence Platform
## Architecture Reference

## Deployed Services

### Platform

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| axiom-ui | React 18 + TypeScript + Vite | 3000 | Unified UI shell |
| axiom-api | Spring Boot 3.x / Java 21 | 8080 | Platform gateway — auth routing, JWT validation, pillar routing, health aggregation |

### Archon — Architecture Reasoning

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| archon-api | Spring Boot 3.x / Java 21 | 8081 | Conversation management, session storage, ADL governance |
| archon-agent | FastAPI + LangGraph / Python 3.11 | 8001 | 13-stage architecture reasoning pipeline |

### SpecWeaver — Requirements Intelligence

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| specweaver-api | Spring Boot 3.x / Java 21 | 8082 | Session management, document ingestion, package generation |
| specweaver-agent | FastAPI + LangGraph / Python 3.11 | 8085 | Extraction, consolidation, classification, gap analysis, conflict detection |

### Lens — Architecture Review Intelligence

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| lens-api | Spring Boot 3.x / Java 21 | 8083 | Review sessions, evidence storage, gap elicitation, review reports |
| lens-agent | FastAPI + LangGraph / Python 3.11 | 8086 | Evidence parsing, framework analysis, risk synthesis, report generation |

### Future pillars

| Pillar | API Port | Agent Port | Status |
|--------|----------|------------|--------|
| Scout — Repository Intelligence | 8083 | 8086 | Not on roadmap |
| Forge — Architecture Enforcement | 8084 | 8087 | Not on roadmap |

### Service topology

```text
Browser
  → axiom-api:8080 (platform gateway — auth + JWT validation + routing)
    → archon-api:8081 (Archon pillar API)
      → archon-agent:8001 (Archon reasoning pipeline)
    → specweaver-api:8082 (SpecWeaver pillar API)
      → specweaver-agent:8085 (SpecWeaver extraction pipeline)
    → lens-api:8083 (Lens pillar API)
      → lens-agent:8086 (Lens review pipeline)
```

### Two-service rule

Each pillar has exactly two services: one API service
(Spring Boot) and one agent service (Python FastAPI).
No pillar may have more than two services.
This is enforced by ADL.

### Cross-pillar communication

Pillars communicate via HTTP only. There are no shared
databases, no shared in-process objects, and no shared
libraries containing business logic between pillars.

### Pillar implementation status

| Pillar | Status | Notes |
|--------|--------|-------|
| Archon | Production-capable | Full 13-stage pipeline + QAW |
| SpecWeaver | Phase 1 active | Extraction + classification |
| Lens | Active | Architecture reviews and gap elicitation |

### Platform service boundaries

ASSERT platform-boundaries {
  axiom-api must not contain JPA entities or Flyway migrations
  axiom-api must not call the LLM directly
  axiom-api must not import archon-api classes
  archon-api trusts X-Axiom-User-Id when AXIOM_GATEWAY_BYPASS=false
  archon-api must not be reachable externally when bypass=false
}

---

# Architecture Guidlines for Copilot
# Version: 1.0
# Owner: Architecture Team
# Last updated: 2025
#
# This file defines structural rules, service boundaries, and invariants
# that ALL code in this repository must conform to.
#
# Copilot and all AI coding assistants must treat this file as
# a hard constraint. When generating code, verify every suggestion
# against the rules below before presenting it.

---

## SYSTEM DEFINITION

DEFINE system ArchonAssistant {
  RESPONSIBILITY: "AI-powered architecture and requirements intelligence platform"
  SERVICES: [axiom-api, archon-api, archon-agent, specweaver-api, specweaver-agent, axiom-ui]
  DATABASES: [PostgreSQL, Qdrant, object storage]
  COMMUNICATION: [HTTP from client to axiom-api, HTTP/SSE between axiom-api and pillar APIs, HTTP/NDJSON between pillar APIs and agents]
  DEPLOYMENT: Docker Compose (local), AKS (production)
}


---

## SERVICE: archon-api (Spring Boot)

DEFINE service archon-api {
  LANGUAGE: Java 21
  FRAMEWORK: Spring Boot 3.3.4
  RESPONSIBILITY: "Archon pillar API — auth, session management, SSE streaming, agent bridge"
  OWNS: [Conversation, Message, ConversationStatus, MessageRole, ArchitectureOutput]
  DOES_NOT_OWN: [ArchitectureContext, pipeline logic, LLM calls, tool execution]
  EXPOSES: [
    POST /api/v1/chat/stream,
    POST /api/v1/conversations,
    POST /api/v1/auth/forgot-password,
    POST /api/v1/auth/reset-password,
    GET /api/v1/auth/reset-password/validate,
    GET /api/v1/conversations/{id}/pipeline-status,
    GET /api/v1/sessions/{id}/messages,
    GET /api/v1/sessions/{id}/architecture,
    GET /api/v1/sessions/{id}/diagram,
    GET /api/v1/sessions/{id}/diagram/{type},
    GET /api/v1/sessions/{id}/fmea-risks,
    GET /api/v1/sessions/{id}/governance,
    GET /api/v1/sessions/{id}/tactics,
    GET /api/v1/sessions/{id}/tactics/summary,
    GET /api/v1/sessions/{id}/build-analysis,
    GET /api/v1/sessions/{id}/build-analysis/conflicts,
    GET /api/v1/conversations/{id}/usage
  ]
  CALLS: [archon-agent via AgentHttpClient]
  ROOT_PACKAGE: com.archon.api
}

ASSERT archon-api {
  MUST use Flyway for all schema changes
    — ddl-auto MUST be "validate", never "create", "update", or "create-drop"

  MUST NOT contain LLM API calls
    — no openai, azure-openai, langchain, or llm client dependencies in pom.xml

  MUST NOT contain pipeline logic
    — no stage orchestration, no tool invocation, no ArchitectureContext manipulation

  MUST use WebClient (not RestTemplate) for all HTTP calls to archon-agent
    — RestTemplate is blocking and will deadlock the SSE response thread

  MUST NOT enable open-in-view
    — spring.jpa.open-in-view MUST be false in application.yml

  MUST stream agent responses as Server-Sent Events
    — ChatController.streamChat() MUST return Flux<AgentResponse>
    — endpoint MUST produce MediaType.TEXT_EVENT_STREAM_VALUE

  PipelineRunService MUST create a run record before the agent stream begins
    — see ASSERT durable_runs above

  MUST persist every user message BEFORE forwarding to agent
    — ConversationService.saveMessage() called with MessageRole.USER before
      AgentBridgeService.stream() is invoked

  MUST persist assistant response AFTER stream completes
    — doOnComplete() callback saves accumulated text, not doOnNext()

  MUST validate all incoming requests
    — @Valid annotation required on all @RequestBody parameters
    — @NotBlank and @Size constraints required on ChatRequest.message

  MUST authenticate service-to-service calls with X-Internal-Secret header
    — AgentHttpClient MUST set this header on every request to archon-agent

  MUST NOT expose internal exceptions to API consumers
    — AgentCommunicationException MUST be caught and mapped to a safe error response

  MUST limit conversation history sent to agent
    — getRecentMessages() MUST be called with limit <= 20 before building AgentRequest

  ASSERT password_reset_security {
    MUST generate reset tokens using java.security.SecureRandom with minimum 32 bytes of entropy
    MUST store only the bcrypt hash of the token in the database
      — the raw token MUST exist only in the email link
    MUST expire tokens after TOKEN_EXPIRY_MINUTES (30)
    MUST enforce single-use tokens
      — used_at MUST be marked on successful consumption
    POST /api/v1/auth/forgot-password MUST return HTTP 200 with an identical response
      regardless of whether the email is registered
    MUST rate limit reset requests to MAX_REQUESTS_PER_HOUR (3) per email address per hour
    MUST validate new password minimum length (12 characters)
      AND reject passwords that match the current password
    EmailService failures MUST NOT propagate to callers
      — email delivery is best-effort only
  }
}

REQUIRE archon-api {
  IF a new JPA entity is added
    THEN a corresponding Flyway migration MUST be created in db/migration/
    AND the migration filename MUST follow pattern V{n}__{description}.sql

  IF a new REST endpoint is added
    THEN it MUST be covered by an integration test using @SpringBootTest
    AND it MUST be documented in this file under EXPOSES

  IF a new external dependency is added to pom.xml
    THEN its purpose MUST be documented in a comment in pom.xml
    AND it MUST NOT duplicate functionality already provided by an existing dependency

  IF open-in-view is set to anything other than false
    THEN the build pipeline MUST fail
}


---

## SERVICE: archon-agent (Python / FastAPI)

DEFINE service archon-agent {
  LANGUAGE: Python 3.11
  FRAMEWORK: FastAPI + LangGraph (Phase 2+)
  RESPONSIBILITY: "LLM orchestration — pipeline execution, tool dispatch, streaming"
  OWNS: [ArchitectureContext, pipeline stages, tool registry, prompt templates]
  DOES_NOT_OWN: [Conversation, Message, session state, JWT auth]
  EXPOSES: [POST /agent/stream, GET /health]
  ROOT_MODULE: app
}

ASSERT archon-agent {
  MUST validate X-Internal-Secret on every request to POST /agent/stream
    — return HTTP 401 if header is absent or does not match INTERNAL_SECRET env var

  MUST stream responses as NDJSON
    — one JSON object per line, each line terminated with \n
    — media_type MUST be "application/x-ndjson"

  weakness_analyzer MUST complete before fmea_analyzer
    — see ASSERT weakness_before_fmea above

  MUST use ArchitectureContext as the single pipeline state object
    — no stage may pass data to another stage except through ArchitectureContext
    — no global variables or module-level state for pipeline data

  MUST use Pydantic models for all inputs and outputs
    — no untyped dict passing across function boundaries in production code
    — raw dicts allowed only in stub/test code

  MUST emit STAGE_START before any work in a stage begins
    AND STAGE_COMPLETE after the stage finishes
    — the client depends on these events for progress display

  MUST emit COMPLETE as the final event in every successful pipeline run
    — payload MUST include conversationId and stages_executed

  MUST emit ERROR event type on unhandled exceptions
    — never let an unhandled exception silently terminate the stream
    — always yield a final ERROR chunk before raising or returning

  MUST NOT call Spring Boot or any archon-api endpoint
    — data flows api → agent only, never agent → api

  MUST NOT store secrets in code
    — INTERNAL_SECRET and OPENAI_API_KEY MUST be read from environment variables
    — no hardcoded keys, tokens, or passwords anywhere in app/

  MUST keep prompt templates in app/prompts/ as .j2 (Jinja2) files
    — no raw prompt strings embedded in tool class bodies (Phase 2+)
    — tool classes MAY contain prompt strings only in Phase 1 stub code

  MUST score all eight Richards architecture styles before selecting
    — layered, modular monolith, microkernel, pipeline,
      service-based, event-driven, microservices, space-based
    — style_selection field must be present in architecture_design
    — style_scores must contain all eight styles

  MUST apply veto rules before finalising style selection
    — a style may not be selected if a veto condition applies

  MUST NOT default to layered architecture when scalability,
  elasticity, or agility characteristics are present with
  non-trivial measurable targets

  MUST include when_to_reconsider_this_style in every design
    — lists the observable conditions that would force a style
      change as the system evolves

  MUST generate between 3 and 5 diagrams per pipeline run
    — never fewer than 3, never more than 5

  MUST always generate c4_container, sequence_primary,
  and sequence_error diagrams
    — these three are mandatory regardless of architecture style

  MUST select diagram types based on architecture style and
  characteristics — not hardcoded

  MUST NOT return diagrams with fewer than 10 non-empty lines
    — shallow diagrams fail the minimum detail requirement

  MUST NOT include ``` fence characters in mermaid_source fields
    — source must be raw Mermaid syntax only
}

ASSERT architecture_override {
  MUST apply pinned style overrides from architecture_override.type
    — a pinned style must be used unless a veto rule applies

  MUST populate override_warning when override conflicts with
  primary characteristics — empty string is not acceptable
  when a poor-fit override is applied

  MUST restrict candidate_set selection to user-provided styles
  only — never select outside the set without explicit warning
}

ASSERT buy_vs_build_analyzer {
  MUST name real products in alternatives_considered
    — invented product names are a hard failure

  MUST set recommendation to "buy" or "adopt" for components
  in the never-build categories (payments, email, SMS, auth
  protocols, DDoS protection, certificate management)

  MUST set conflicts_with_user_preference accurately when a
  recommendation contradicts a user-stated preference

  MUST provide rationale of at least 60 characters specific
  to this system — generic rationale is rejected by validation
}

ASSERT tactics_advisor {
  MUST only recommend tactics from the Bass, Clements, Kazman catalog
    — "Software Architecture in Practice", 4th ed., SEI/Addison-Wesley 2021
    — no invented or unattributed tactics

  MUST produce a minimum of 4 validated tactic recommendations per run
    — fewer than 4 passing validation is treated as a warning condition

  MUST validate each tactic before writing to ArchitectureContext
    — tactic_name MUST be non-blank
    — description MUST be >= 20 characters
    — concrete_application MUST be >= 30 characters (system-specific, not generic)
    — effort MUST be one of: low | medium | high
    — priority MUST be one of: critical | recommended | optional
    — implementation_examples MUST be a non-empty list

  MUST execute as pipeline stage 4b
    — AFTER characteristic_inference (stage 4)
    — BEFORE conflict_analysis (stage 5)
    — reads context.characteristics (MUST be populated)
    — reads context.architecture_design (optional — logs WARNING if absent)

  MUST write to context.tactics and context.tactics_summary only
    — MUST NOT mutate characteristics, architecture_design, or any stage output
      written before stage 4b
}

REQUIRE archon-agent {
  IF a new pipeline stage is added
    THEN it MUST be added as a LangGraph node (Phase 2+)
    AND it MUST read from and write to ArchitectureContext only
    AND it MUST emit STAGE_START and STAGE_COMPLETE events
    AND it MUST be listed in this file under the pipeline section below

  IF a new tool is added
    THEN it MUST be registered in the tool registry (Phase 2+)
    AND it MUST have a Pydantic input model and output model
    AND it MUST be independently testable with no LLM dependency using mocked LLM calls

  IF ArchitectureContext gains a new field
    THEN the field MUST have a default value so existing runs are not broken
    AND the field MUST be documented with an inline comment stating which stage populates it

  IF a prompt template is changed
    THEN the change MUST be tested against the evaluation set (3 representative inputs)
    BEFORE being merged
}


---

## SERVICE: axiom-ui (React / Vite)

DEFINE service axiom-ui {
  LANGUAGE: TypeScript
  FRAMEWORK: React 18, Vite, Tailwind CSS
  RESPONSIBILITY: "Browser SPA — auth, streaming chat, architecture visualization, governance dashboard"
  OWNS: [UI state (Zustand), views, components, hooks]
  DOES_NOT_OWN: [Conversation persistence, pipeline logic, LLM calls, JWT issuance]
  CONSUMES: [
    POST /api/v1/auth/token,
    POST /api/v1/chat/stream (SSE via fetch + ReadableStream),
    GET /api/v1/sessions/{id}/architecture,
    GET /api/v1/sessions/{id}/diagram,
    GET /api/v1/sessions/{id}/adl,
    GET /api/v1/sessions/{id}/trade-offs,
    GET /api/v1/sessions/{id}/weaknesses,
    GET /api/v1/sessions/{id}/fmea-risks,
    GET /api/v1/sessions/{id}/governance,
    GET /api/v1/sessions/{id}/tactics,
    GET /api/v1/sessions/{id}/tactics/summary
  ]
  ROOT_DIR: axiom-ui/src
}

ASSERT axiom-ui {
  MUST use fetch + ReadableStream for the SSE streaming endpoint
    — EventSource MUST NOT be used (POST body is required)

  MUST proxy all API calls through relative /api/* paths
    — MUST NOT reference localhost:8080 or any absolute backend URL in source code

  MUST NOT store JWT in localStorage
    — JWT is held only in Zustand in-memory state

  MUST NOT perform fetch calls inside React components
    — all HTTP calls live in src/api/ modules only

  MUST render MermaidDiagram with error handling
    — if mermaid.render() throws, display error + raw source fallback

  MUST disable Submit button while streaming is in progress
    — prevents duplicate pipeline runs

  MUST handle unknown event types in handleEvent without throwing
    — unknown types are silently ignored

  MUST provide empty-state UI for all views when no data is loaded

  MUST run as non-root user in the production Docker image
}

REQUIRE axiom-ui {
  IF a new pipeline stage is added
    THEN PIPELINE_STAGES array in src/types/api.ts MUST be updated
    AND STAGE_LABELS in src/components/StageProgress.tsx MUST be updated

  IF a new governance endpoint is added to the API
    THEN a corresponding function MUST be added in src/api/governance.ts
    AND the GovernanceView MUST add a tab for it

  IF a new SSE event type is introduced
    THEN handleEvent in the Zustand store MUST handle it
    — unknown types are still silently ignored
}


---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RELIABILITY CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFINE run_lifecycle {
  A pipeline run is a first-class durable entity.
  The SSE stream is a VIEW over a run, not the run itself.
  Stream loss, browser refresh, proxy timeout, or container
  restart must not change the run's completion status.
}

ASSERT weakness_before_fmea {
  weakness_analyzer MUST complete before fmea_analyzer begins.
  asyncio.gather() MUST NOT be used for weakness_and_fmea_node.
  FMEA prompt receives populated weaknesses context always.
  REASON: FMEA cascading failure analysis depends on weakness
  inventory. Parallel execution silently degrades FMEA quality.
}

ASSERT review_health_visible {
  Every review sub-node MUST record success or failure in
  sub_review_results regardless of outcome.
  governance_score_confidence MUST be set accurately:
    high        = all four sub-reviews succeeded
    partial     = 1-3 sub-reviews succeeded
    low         = only score_governance succeeded
    unavailable = score_governance itself failed
  A governance score of 75 with failed sub-reviews MUST be
  distinguishable from a governance score of 75 with all
  sub-reviews passing.
  The UI MUST show a degradation warning when review_completed_fully
  is false.
}

ASSERT sse_keepalive {
  The pipeline MUST emit SSE comment lines (": heartbeat")
  every 15 seconds during stage execution.
  Comment lines MUST be emitted without waiting for a stage
  to complete — they must interleave with stage execution.
  REASON: Prevents proxy idle timeout disconnections during
  long-running stages (architecture_generation, review).
}

ASSERT durable_runs {
  pipeline_runs table MUST contain one record per pipeline
  execution created before the agent stream begins.
  pipeline_events table MUST contain an append-only log of
  every SSE event emitted.
  PipelineRunService MUST persist events before forwarding
  them to the SseEmitter.
  Run status MUST be updated to COMPLETED or FAILED when the
  corresponding event arrives.
  A run with status RUNNING after the stream closes represents
  an interrupted run, not a completed one.
  GET /api/v1/sessions/{id}/run/status MUST be available for
  clients to check run state after reconnection.
  GET /api/v1/sessions/{id}/run/stream MUST replay all
  persisted events before continuing live.
}

ASSERT sseemitter_timeout {
  SseEmitter timeout MUST be 600 seconds minimum.
  AgentHttpClient WebClient timeout MUST match SseEmitter timeout.
  REASON: Review re-iteration can run the full pipeline twice.
  180 seconds is insufficient for re-iteration runs even with
  keepalive comments preventing proxy timeouts.
}

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTRACT HARDENING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFINE contract_hardening_intent {
  Every pipeline stage that produces JSON output MUST pass a
  Pydantic-derived JSON schema to the LLM provider via the
  provider-native structured output mechanism.
  Schema enforcement exists to reduce silent garbage-in
  propagation through the pipeline.
  A single repair attempt is allowed per stage before the
  stage is declared failed.
}

ASSERT structured_output_enforcement {
  Every tool that calls llm_client.complete() with
  response_format="json" MUST also pass output_schema and
  schema_name from app.llm.schemas.SCHEMAS.
  SCHEMAS is the single source of truth — schemas must not be
  defined inline inside tool classes.
  Schema keys MUST match stage names used in ORDERED_STAGES.
}

ASSERT provider_schema_enforcement {
  When output_schema is provided and the LLM provider is openai:
    — The provider MUST be called with {"type": "json_schema",
      "json_schema": {"name": schema_name, "strict": true, "schema": ...}}.
  When the provider is ollama:
    — The provider MUST be called with format equal to the output_schema dict.
    — REASON: Ollama supports native schema-constrained generation via format.
  When no output_schema exists for a JSON stage:
    — format="json" or response_format={"type": "json_object"} is acceptable.
}

DEFINE COMPONENT LLMClient AS app.llm.client {
  Provider-abstracted LLM client. Supports ollama for local inference and
  openai for production inference. Selected via LLM_PROVIDER environment
  variable. All pipeline code is provider-agnostic; only LLMClient knows
  which provider is active.

  Model tiering applies to Ollama only. FAST_MODEL_STAGES receive the fast
  model for short structured output generation. All other stages receive
  the primary model for deep reasoning. Model selection is transparent to
  callers.

  Context budgeting lives in app.llm.budget. High-context stages apply
  truncation before prompt rendering to avoid silent truncation by Ollama's
  hard num_ctx limit.
}

DEFINE COMPONENT OllamaContainer AS infrastructure {
  Local inference container running ollama/ollama:latest on port 11434.
  GPU passthrough is configured by Docker deploy.resources. Models are pulled
  by the ollama-init init container and stored in the named Docker volume
  archon-ollama-models.
}

ASSERT llm_provider_abstraction {
  All pipeline tools and workshop nodes MUST call LLMClient.complete() with
  a stage_name parameter.

  No pipeline code outside app.llm.client MUST reference the Ollama API or
  OpenAI API directly.

  FAST_MODEL_STAGES is the authoritative list of stages that use the fast
  model. Adding a stage to the pipeline without considering its model tier
  is prohibited.

  Context budgeting MUST be applied before rendering any prompt that passes
  lists of JSON objects with more than 10 items to the LLM.
}

ASSERT ollama_structured_output {
  When provider=ollama, the format parameter MUST be set to the output_schema
  dict when one is provided.

  Passing format="json" without a schema is acceptable only when no Pydantic
  model exists for the stage output.

  OLLAMA_TEMPERATURE MUST be <= 0.3 for any stage that uses structured output.
  Higher temperatures degrade JSON schema compliance.
}

ASSERT single_repair_per_stage {
  When a tool's JSON parse fails after the initial LLM call,
  BaseTool.attempt_repair() MUST be called exactly once.
  attempt_repair() constructs a targeted repair prompt including:
    — The first 500 characters of the failed response.
    — The specific JSON parse error.
    — The original task description.
  The repair call MUST pass the same output_schema and schema_name.
  If the repair call itself fails with LLMCallException,
  ToolExecutionException is raised immediately — no second repair.
  If the repaired JSON still fails to parse, ToolExecutionException
  is raised with the parse error — no further attempts.
}

ASSERT supporting_stage_resilience {
  The pipeline MUST NOT abort when a supporting stage fails.
  CORE_STAGES = {requirement_parsing, requirement_challenge,
                 characteristic_inference, architecture_generation}
  All other stages are SUPPORTING stages.
  When a SUPPORTING stage raises ToolExecutionException:
    — The gap is recorded in context.pipeline_gaps.
    — context.has_gaps is set to True.
    — The stage emits STAGE_COMPLETE with status="completed_with_gaps".
    — The pipeline continues to the next stage.
  When a CORE stage raises ToolExecutionException:
    — The pipeline emits ERROR and halts immediately.
  The COMPLETE event MUST include has_gaps and pipeline_gaps fields.
}

ASSERT diagram_generation_per_type {
  DiagramGeneratorTool MUST generate diagrams via one LLM call
  per selected diagram type (_generate_single_diagram per type).
  A single batch call for all types is PROHIBITED.
  REASON: Focused per-type calls improve diagram quality by
  giving the model full context budget for each diagram.
  Partial success is preferred — only raise if ALL types fail.
  diagram_generation STAGE_COMPLETE payload MUST include
  generation_method="per_type_sequential" and failed_types=[...].
}

ASSERT gap_visibility_in_ui {
  The UI MUST display an amber warning indicator on any stage
  whose STAGE_COMPLETE payload has status="completed_with_gaps".
  The UI MUST display a banner when the COMPLETE event has
  has_gaps=true, informing the user that some optional stages
  were skipped and the architecture is based on partial analysis.
  The warning MUST be visually distinct from both the success
  state and the ERROR state.
}

## PIPELINE DEFINITION

DEFINE pipeline ArchonPipeline {
  ENTRY_POINT: POST /agent/stream
  STATE_OBJECT: ArchitectureContext
  MAX_ITERATIONS: 2
  PARALLELISM: stages 9 and 10 run concurrently via asyncio.gather()

  STAGES: [
    1  requirement_parsing       — RequirementParser tool
    2  requirement_challenge     — RequirementChallengeEngine tool
    3  scenario_modeling         — ScenarioModeler tool
    4  characteristic_inference  — CharacteristicReasoningEngine tool
    4b tactics_recommendation   — TacticsAdvisor tool (Bass/Clements/Kazman catalog)
    5  conflict_analysis         — CharacteristicConflictAnalyzer tool
    6  architecture_generation   — ArchitectureGenerator tool
    6b buy_vs_build_analysis     — BuyVsBuildAnalyzerTool
    7  diagram_generation        — DiagramGenerator tool
    8  trade_off_analysis        — TradeOffEngine tool
    9  adl_generation            — ADLGeneratorV2 tool
    10 weakness_analysis         — WeaknessAnalyzer tool   [parallel with 11]
    11 fmea_analysis             — FMEAPlus tool           [parallel with 10]
    12 architecture_review       — ReviewAgent (separate LangGraph graph)
  ]
}

ASSERT ArchonPipeline {
  MUST execute stages in order 1 → 8, then 9+10 in parallel, then 11
    — stage N MUST NOT begin until stage N-1 has written its output to ArchitectureContext

  MUST NOT pass data between stages via function arguments
    — all inter-stage data flows through ArchitectureContext fields only

  MUST trigger re-iteration if ReviewAgent sets should_reiterate = true
    AND ArchitectureContext.iteration < 2
    — if iteration >= 2, proceed to COMPLETE regardless of governance score
    — RE_ITERATE event MUST be emitted before restarting the pipeline
    — iteration counter MUST be incremented before recursive call

  ReviewAgent MUST receive a read-only snapshot of ArchitectureContext
    — ReviewAgent MUST NOT mutate the forward-pass ArchitectureContext
    — ReviewAgent writes to a separate ReviewContext object only
    — deep copy via ReviewContext._build_review_context()

  FMEA+ and WeaknessAnalyzer MUST execute in parallel (asyncio.gather)
    — merged into a single pipeline stage: weakness_and_fmea
    — both tools write to separate ArchitectureContext fields (no conflict)
}

DEFINE sub-graph ReviewAgent {
  ENTRY: ArchitectReviewAgent.run(context)
  STATE_OBJECT: ReviewContext (deep copy of ArchitectureContext fields)
  ISOLATION: ReviewContext is never a reference to the live ArchitectureContext

  NODES: [
    1  assumption_challenger  — challenges 5-10 implicit assumptions in the design
    2  trade_off_stress       — stress-tests 2-6 trade-off decisions
    3  adl_audit              — audits ADL for 3-8 coverage issues
    4  governance_scorer      — scores across 4 dimensions (25 pts each, total 100)
  ]

  OUTPUTS_TO_CONTEXT: [
    review_findings          — combined findings from nodes 1-3
    governance_score         — integer 0-100
    governance_score_breakdown — {requirement_coverage, architectural_soundness, risk_mitigation, governance_completeness}
    improvement_recommendations — ranked list of actionable improvements
    should_reiterate         — boolean (true if score < threshold AND iteration < max)
    review_constraints       — high-priority constraints injected into re-iteration Stage 2
  ]
}


---

## DATA LAYER

DEFINE database PostgreSQL {
  OWNS: [conversations table, messages table, fmea_risks table, governance_reports table]
  USED_BY: [archon-api only]
  SCHEMA_MANAGEMENT: Flyway

  TABLE fmea_risks {
    — stores FMEA+ failure modes per conversation
    — columns: id (UUID PK), conversation_id (FK), risk_id, failure_mode, component,
      cause, effect, severity (1-10), occurrence (1-10), detection (1-10),
      rpn (computed S×O×D), current_controls, recommended_action,
      linked_weakness, linked_characteristic, created_at
    — ordered by rpn DESC for risk-priority queries
  }

  TABLE governance_reports {
    — stores governance scoring per iteration per conversation
    — columns: id (UUID PK), conversation_id (FK), iteration, governance_score (0-100),
      requirement_coverage (0-25), architectural_soundness (0-25),
      risk_mitigation (0-25), governance_completeness (0-25),
      justification, should_reiterate, review_findings (JSONB),
      improvement_recommendations (JSONB), created_at
    — one row per iteration (max 2 per conversation)
  }

  TABLE token_usage {
    — stores per-stage LLM token consumption for cost tracking
    — columns: id (UUID PK), conversation_id (FK), stage (TEXT),
      model (TEXT), input_tokens (INT), output_tokens (INT),
      total_tokens (INT), estimated_cost (NUMERIC 12,6), created_at
    — indexed on conversation_id and created_at
    — one row per stage per pipeline run
  }
}

DEFINE database Qdrant {
  OWNS: [architecture pattern embeddings, past design vectors]
  USED_BY: [archon-agent only]
  PURPOSE: "Semantic memory — retrieve similar past architectures at inference time"
  COLLECTION: architecture_patterns {
    EMBEDDING_MODEL: text-embedding-3-small
    DIMENSION: 1536
    DISTANCE: cosine
    POINT_PAYLOAD: [conversation_id, domain, system_type, architecture_style, characteristic_names, stored_at]
  }
}

DEFINE component MemoryStore {
  LANGUAGE: Python
  MODULE: app.memory.store
  RESPONSIBILITY: "Qdrant-backed vector memory for architecture pattern storage and retrieval"
  METHODS: [
    _ensure_collection()  — create Qdrant collection if not exists (called at startup),
    store_design()        — embed requirements and upsert into Qdrant (fire-and-forget),
    retrieve_similar()    — embed requirements and search Qdrant for similar past designs
  ]
  INVARIANT: All public methods MUST catch exceptions and log warnings — never raise to caller
}

ASSERT data-layer {
  MUST NOT allow archon-agent to connect to PostgreSQL directly
    — agent has no PostgreSQL connection string in its environment

  MUST NOT allow archon-api to connect to Qdrant directly
    — api has no Qdrant connection string in its environment

  MUST store all structured agent outputs (ADL, trade-offs, weaknesses) as JSONB
    in messages.structured_output
    — architecture_outputs table is the sole exception (Phase 3+ for query-friendly access)
    — fmea_risks and governance_reports tables are exceptions (Phase 5 governance pipeline)
    — do not create additional separate tables for each output type beyond these

  MUST use UUID primary keys on all tables
    — no integer or serial primary keys
}


---

## PRODUCTION OPERATIONS

DEFINE infrastructure Production {
  PLATFORM: Azure Kubernetes Service (AKS)
  CHART: helm/axiom (Helm v3)
  OBSERVABILITY: OpenTelemetry → Jaeger (traces), Prometheus (metrics)
  SECRETS: Azure Key Vault via CSI SecretProviderClass
  INGRESS: NGINX Ingress Controller with TLS via cert-manager
}

ASSERT observability-stack {
  MUST export distributed traces via OpenTelemetry Protocol (OTLP/gRPC)
    — Python agent uses opentelemetry-sdk + OTLPSpanExporter
    — Spring Boot API uses Micrometer OTel bridge for automatic instrumentation

  MUST propagate W3C TraceContext headers across service boundaries
    — AgentHttpClient MUST carry traceparent / tracestate headers to agent
    — correlation of api → agent spans is required for end-to-end trace views

  MUST emit structured JSON logs in production
    — Python agent uses structlog with JSON renderer
    — Spring Boot API includes traceId, spanId, conversationId in log pattern

  MUST record per-tool OpenTelemetry spans
    — span name pattern: tool.{tool_name}
    — attributes: conversation_id, stage_name, llm.input_tokens, llm.output_tokens

  MUST track pipeline-level metrics
    — active_pipeline_runs (UpDownCounter)
    — llm_tokens_total (Counter, labels: stage, model, direction)
    — stage_duration_seconds (Histogram, label: stage)
}

ASSERT resilience {
  MUST protect AgentHttpClient with a circuit breaker (Resilience4j)
    — sliding-window size, failure-rate threshold, and wait duration are configurable
    — open circuit MUST return HTTP 503 to the API caller

  MUST protect AgentHttpClient with a rate limiter (Resilience4j)
    — limit-for-period, refresh period, and timeout are configurable
    — exceeded rate MUST return HTTP 429 to the API caller

  MUST handle CircuitBreaker and RateLimiter exceptions in GlobalExceptionHandler
    — CallNotPermittedException → 503 Service Unavailable
    — RequestNotPermitted → 429 Too Many Requests
}

ASSERT cost-tracking {
  MUST track LLM token usage per stage per pipeline run
    — recorded via contextvars-based PipelineTokenUsage tracker in agent
    — attached to the COMPLETE event payload as token_usage dict

  MUST persist token usage to the token_usage table via the API
    — ChatService extracts token_usage from COMPLETE payload and delegates to UsageService
    — one row per stage, per model, per pipeline run

  MUST expose per-conversation usage summary via REST
    — GET /api/v1/conversations/{id}/usage
    — response includes total input/output/tokens, estimated cost, and per-stage breakdown

  MUST estimate cost using configurable per-model pricing
    — default rates for gpt-4o and gpt-4o-mini are provided
    — unknown models default to zero cost (safe fallback)
}

ASSERT deployment {
  MUST deploy to AKS via Helm chart in helm/axiom/
    — values.yaml MUST parameterise all images, replica counts, resource limits,
      and secret references — no hardcoded cluster-specific values in templates

  MUST use HorizontalPodAutoscaler for agent and api deployments
    — conditionally enabled via .Values.{service}.hpa.enabled
    — CPU-based scaling with configurable min/max replicas and target utilization

  MUST restrict database network access via NetworkPolicy
    — PostgreSQL accepts ingress only from agent and api pods
    — Qdrant accepts ingress only from agent pods

  MUST source production secrets from Azure Key Vault
    — SecretProviderClass creates a Kubernetes secret (archon-secrets)
    — workload identity (managed identity) is used — no service principal credentials stored

  MUST use StatefulSets with PersistentVolumeClaims for postgres and qdrant
    — data persistence survives pod restarts
    — storageClass is configurable (default: managed-premium)
}

ASSERT tls_required {
  The ingress MUST terminate TLS using a certificate issued by
  Let's Encrypt via cert-manager.
  The ingress annotation ssl-redirect MUST be true so all HTTP
  traffic is redirected to HTTPS automatically.
  Self-signed certificates MUST NOT be used in any environment.
  The TLS issuer MUST be letsencrypt-staging for initial setup
  and letsencrypt-prod once staging is verified.
  Certificate renewal is handled automatically by cert-manager.
  No manual certificate rotation process exists or is required.
}


---

## SECURITY

ASSERT security {
  MUST use X-Internal-Secret header for all api → agent calls
    — secret MUST come from environment variable, never hardcoded
    — agent MUST return HTTP 401 if header is missing or incorrect

  MUST NOT log secret values
    — INTERNAL_SECRET, JWT_SECRET, OPENAI_API_KEY MUST never appear in log output

  MUST disable CSRF protection on the API layer
    — this is a stateless API consumed by non-browser clients
    — CSRF protection is inappropriate and must remain disabled

  MUST run application containers as non-root users
    — Dockerfile MUST create and switch to a non-root user before CMD/ENTRYPOINT

  MUST NOT store API keys in .env files committed to version control
    — .env MUST be in .gitignore
    — only .env.example (with empty values) is committed
}

REQUIRE security {
  IF JWT authentication is added (Phase 2)
    THEN the DEV_USER constant in ChatController MUST be removed
    AND all endpoints under /api/v1/ MUST require a valid JWT
    AND SecurityConfig MUST be updated to reflect this

  IF a new secret or credential is introduced
    THEN it MUST be added to .env.example with an empty value
    AND documented in this file under the security section
}


---

## COMMUNICATION CONTRACT

DEFINE contract api-to-agent {
  PROTOCOL: HTTP POST
  PATH: /agent/stream
  REQUEST_FORMAT: JSON body — AgentRequest schema
  RESPONSE_FORMAT: NDJSON stream — one AgentResponseChunk per line
  AUTH: X-Internal-Secret header
  TIMEOUT: 120 seconds
}

DEFINE contract client-to-api {
  PROTOCOL: HTTP POST with SSE response
  PATH: /api/v1/chat/stream
  REQUEST_FORMAT: JSON body — ChatRequest schema
  RESPONSE_FORMAT: text/event-stream — one AgentResponse per SSE event
  AUTH: none in Phase 1, JWT Bearer in Phase 2+
}

ASSERT communication-contract {
  MUST NOT change the AgentResponseChunk event type enum values
    — EventType values (CHUNK, STAGE_START, STAGE_COMPLETE, TOOL_CALL,
      COMPLETE, RE_ITERATE, ERROR) are part of the client contract
    — adding new values is allowed, removing or renaming existing values is not

  MUST NOT change the /agent/stream request field names without a migration plan
    — conversationId, userMessage, mode, history, context are stable field names

  MUST use application/x-ndjson as media type for api → agent responses
  MUST use text/event-stream as media type for client → api responses
}


---

## OBSERVABILITY

ASSERT observability {
  MUST include conversation_id on every log line during request processing
    — use MDC (Java) or structlog context vars (Python)

  MUST instrument every tool call as a child OpenTelemetry span (Phase 2+)
    — span name pattern: tool.{tool_name}
    — span MUST include conversation_id and stage_name as attributes

  MUST NOT log message content at INFO level or above
    — user message content is sensitive and MUST only appear at DEBUG level
    — never log LLM responses at INFO or above

  MUST expose /actuator/health (Spring Boot) and /health (FastAPI)
    — both MUST return HTTP 200 with a status field when the service is healthy
}


---

## WHAT COPILOT MUST ALWAYS DO

When generating code for this project, Copilot MUST:

1. Read this file before generating any code.

2. Place new Java classes in the correct package under com.archon.api.
   Never create classes outside the root package.

3. Never write raw SQL outside of Flyway migration files.
   JPA repositories handle all queries; JPQL is allowed in @Query annotations.

4. Never add spring.jpa.hibernate.ddl-auto values other than "validate".

5. Never use RestTemplate. Always use WebClient for HTTP calls.

6. Never call the OpenAI or Azure OpenAI API from archon-api.
   All LLM calls belong exclusively in archon-agent.

7. Never add pipeline logic to ChatService or AgentBridgeService.
   Those classes bridge HTTP only — they contain no domain logic.

8. Always add a default value when adding a field to ArchitectureContext.
   New fields must never break existing pipeline runs.

9. Always emit STAGE_START before a stage begins and STAGE_COMPLETE
   after it finishes. Never skip these events.

10. Never hardcode secrets. Always read from environment variables.

## WHAT COPILOT MUST NEVER DO

1. Never set ddl-auto to anything other than "validate".
2. Never import RestTemplate in any class.
3. Never write LLM calls in the Spring Boot service.
4. Never mutate ArchitectureContext from the ReviewAgent.
5. Never remove or rename existing AgentResponse.EventType enum values.
6. Never log secrets, API keys, or user message content at INFO or above.
7. Never create a new table for structured agent output beyond architecture_outputs
   — use messages.structured_output JSONB for all other output types.
8. Never skip the X-Internal-Secret validation in the agent endpoint.
9. Never set open-in-view to true.
---

## QUALITY ATTRIBUTE WORKSHOP

The Quality Attribute Workshop (QAW) is a first-class, separately bounded module
within Archon. It implements the SEI QAW methodology (CMU/SEI-2001-TR-020) and
the scenario elicitation framework from Bass, Clements, Kazman "Software
Architecture in Practice" 4th ed.

### Module boundaries

ASSERT: app.workshop MUST NOT import from app.pipeline.
  Rationale: The workshop is a pre-architecture elicitation tool. Coupling it to
  the pipeline would create a dependency inversion and compromise testability.

ASSERT: app.workshop MUST NOT import from app.tools.
  Rationale: The workshop uses only the shared LLM client. No RAG, ADR lookup,
  cost-estimator, or other pipeline tools are permitted inside workshop modules.

ASSERT: In the LangGraph graph built by QualityAttributeWorkshopAgent._build_graph(),
  the identify_gaps node MUST appear before elicit_scenarios in the edge sequence,
  and reconcile_gaps → resolve_questions → elicit_scenarios MUST preserve that order.
  Rationale: ADL-038 — "ask before you assert". Gaps must be identified before
  scenarios are elicited so that the agent never treats speculation as evidence.
  Answers must bind to existing attributes (resolve_questions) before new scenarios
  are elicited so structured state stays consistent.

ASSERT scenario_primary_artifact {
  MUST elicit scenarios as primary artifacts using elicit_scenarios_node before
    inferring attributes.
  MUST infer quality attributes from scenarios using infer_attributes_from_scenarios_node —
    not directly from keywords or elicitation categories alone.
  MUST NOT mark a scenario as complete unless stimulus, response, and response_measure
    fields meet substance thresholds — enforced by QAScenario.compute_completeness().
  MUST surface scenarios as first-class UI artifacts in a dedicated Scenarios tab.
  The old elicit_attributes_node approach of deriving attributes directly from context
    is permanently retired.
}

ASSERT gap_reconciliation {
  MUST model gaps as confidence-scored uncertainty windows with resolution_confidence
    in the range 0.0–1.0.
  MUST run GapReconciler after every identify_gaps call (reconcile_gaps node).
  MUST evaluate accumulated evidence across all turns — not only the latest input —
    when scoring gaps.
  MUST narrow residual_question when confidence ≥ 0.5.
  MUST NOT keep asking the original broad gap question when residual_question has been set.
  Boolean filled is derived from resolution_confidence and priority thresholds — never set
    as a standalone persisted flag (legacy JSON is migrated on load).
}

ASSERT consolidation_threshold {
  MUST NOT run ConsolidationEngine when attribute count is below
    MIN_ATTRIBUTES_FOR_CONSOLIDATION (6).
  MUST NOT merge attributes that require different architectural tactics to achieve,
    even if they are related.
  Distinct attributes that must never be merged:
    Availability and Recoverability; Performance and Scalability; Auditability and
    Observability; Data Integrity and Security.
}

ASSERT attribute_consolidation {
  ConsolidationEngine MUST run after infer_attributes_from_scenarios when the attribute
    count meets MIN_ATTRIBUTES_FOR_CONSOLIDATION, and after every call to
    generate_from_current_evidence when the same threshold is met.
  Rationale: Without consolidation the attribute list grows unchecked — aliases accumulate,
  semantically equivalent concerns are tracked separately, and the cap is not enforced.

  ConsolidationEngine._separate_non_qa MUST move non-measurable concerns
    (regulatory constraints, team-size concerns, delivery pressure) out of
    context.attributes and into context.non_qa_concerns.
  Rationale: Non-QA concerns inflate the attribute count and confuse the LLM
  when it reads the attribute list.

  The consolidation node MUST appear after infer_attributes_from_scenarios and before
    check_transition in the sequence:
    analyze_input → identify_gaps → reconcile_gaps → resolve_questions → elicit_scenarios →
    infer_attributes_from_scenarios → consolidation → check_transition → generate_response
}

ASSERT answer_artifact_binding {
  MUST run AttributeQuestionResolver after gap reconciliation
    and before scenario elicitation on every turn that has attributes with open questions.
  resolve_questions node MUST search ALL accumulated evidence,
    not just the latest turn's input.
  When a question on an attribute is resolved:
    MUST remove it from open_questions
    MUST add the answer to resolved_answers
    MUST update the relevant scenario field if applicable
    MUST recompute scenario completeness after field update (via QAScenario model lifecycle)
    MUST set last_update_summary on the attribute
    MUST increment questions_resolved_count
    MUST NOT leave open_questions growing indefinitely —
    any question answerable from accumulated evidence MUST
    be resolved by this node when the resolver LLM pass succeeds.
  The resolve_questions graph step runs whenever the pipeline executes —
    answer binding is not skipped by workshop phase when open questions exist.
}

ASSERT scenario_extraction {
  MUST search ALL accumulated evidence for implicit scenarios —
    not only the latest turn's input.
  MUST recognise implicit scenarios in:
    incident stories, fear statements, operational descriptions,
    and failure examples.
  elicit_scenarios prompt MUST receive all_evidence (full
    turn history) not just known_facts or latest_input alone.
  MUST NOT re-derive a scenario that is already in existing_scenarios (same scenario_id).
}

ASSERT completeness_invariant {
  QAScenario.compute_completeness MUST be reflected after construction via model_post_init —
    this is enforced by ADL-042 tests.
  MUST recompute completeness after every scenario field
    update in resolve_questions, elicit_scenarios, and infer_attributes nodes
    (QAScenario post-init or explicit field rebuild).
  No Python code in app/workshop should assign completeness = 'complete' as a string
    literal except inside compute_completeness / model lifecycle — enforced by CI grep.
}

ASSERT context_budget {
  MAX_CONTEXT_TOKENS = 60,000 (character-count / 4 proxy).
  When the estimated context size exceeds this, prepare_context_for_prompt
  MUST switch to the summarised view rather than passing the full context.
  Rationale: Prevents silent context truncation at the LLM boundary.

  MAX_SINGLE_INPUT_CHARS = 3,000. When a single user input exceeds this,
  a warning MUST be surfaced in the UI (amber banner). Input is not blocked.
  Rationale: Very long inputs degrade question quality and fill the context
  budget in a single turn.
}

ASSERT phase_transition {
  Phase transition MUST be evidence-based, not turn-count-based.
  The following table defines the minimum evidence required:

  input_analysis      → business_context:      first turn complete (always advance)
  business_context    → usage_context:          all business_context gaps filled
  usage_context       → technical_context:      all usage_context gaps filled
  technical_context   → risk_priority:          all technical_context gaps filled
  risk_priority       → scenario_brainstorm:    zero critical open gaps
                                                OR (≥3 confirmed/inferred attrs
                                                AND ≤2 critical open AND turn ≥ 4)
  scenario_brainstorm → scenario_refinement:    ≥3 attributes with partial+ scenarios
  scenario_refinement → attribute_consolidation: ≥5 attributes with partial+ scenarios
  attribute_consolidation → validation:         LLM signal only
  validation          → complete:               LLM signal only

  MUST NOT advance phase based on turn count alone.
}

ASSERT user_controlled_generation {
  MUST expose generate action after the first conversation turn
    — never gated on gap count or completion level

  MUST provide a readiness assessment before generation
    — the user makes an informed decision, not a blind one

  MUST generate from whatever evidence exists when requested
    — the generate endpoint MUST NOT return 4xx based on
      gap count or elicitation confidence level

  MUST keep the session open after generation
    — is_complete MUST NOT be set to true by the generate action
    — the user continues refining, the session stays active

  MUST mark attributes as stale when new input arrives
    after a generation — attributes_stale = true

  MUST label generated attributes with the generation pass
    number — attributes from pass 1 vs pass 2 must be
    distinguishable in the UI

  MUST show the ReadinessModal when the user previews
    before generating — the modal is informational, not a gate

  MUST present "Generate now anyway" and "Keep going" as
    equal weight actions in the ReadinessModal — neither is
    primary, neither is discouraged
}

### Persistence model

Spring Boot owns all workshop persistence.
- workshop_sessions: one row per session; context_json JSONB holds full WorkshopContext.
- workshop_attributes: denormalised mirror of confirmed attributes (queryable by confidence/importance).
- workshop_messages: append-only conversation record (one row per turn).

The Python agent is stateless. Spring Boot sends the full context_json on every
turn and receives an updated context back. This means the agent can be restarted
or scaled horizontally without session affinity.

### Pipeline bridge (sendToPipeline)

When hasSufficientAttributes is true, the user may bridge the workshop into the
main pipeline. WorkshopService.sendToPipeline() formats the structured summary as
natural language prose (NOT raw JSON) and injects it as the first user message in
a new Conversation. The existing pipeline then processes it transparently.

NEVER pass structured JSON directly into a Conversation message via the pipeline
bridge — it must always be prose so the requirement_parsing stage works correctly.

ASSERT utility_tree_generation {
  MUST call has_sufficient_for_utility_tree before invoking the LLM.
    — UtilityTreeGenerator.generate() MUST return None when the property
      is False, without making any LLM call.

  MUST require at least 5 scenarios with completeness in (complete, partial,
  needs_measure) across at least 3 distinct exercises_attributes values.
    — aspirational scenarios MUST NOT count toward either threshold.

  MUST return the existing utility_tree unchanged when the LLM call fails.
    — partial state is preserved; never discard a previously generated tree.

  MUST NOT generate utility trees from aspirational scenarios.
    — the threshold check enforces this; do not special-case or bypass it.
}

ASSERT implication_synthesis {
  MUST output requirements, not mechanisms.
    — an implication states what must be true about the system; the
      architecture pipeline decides how to satisfy it.

  MUST NOT contain names of specific architectural mechanisms, patterns,
  or technologies.

  Prohibited terms in implication text:
    async worker pool, consensus protocol, circuit breaker, fallback handler,
    local state store, event sourcing, saga pattern, CQRS, outbox pattern,
    distributed lock, message queue, message broker, load balancer, API gateway,
    service mesh, or any specific technology product name

  MUST include a tradeoff statement describing which quality attribute is
  being deprioritised to satisfy the requirement.

  MUST include a measurable_condition field — extracted from the scenario
  response_measure where available.

  MUST validate implications against the prohibited mechanism term list and
  log WARNING for each violation.

  ASSERT send-to-pipeline-formatter {
    MUST include ALL quality attributes — not a subset
    MUST include full scenario structure (all six parts) for architectural
      driver scenarios
    MUST include tradeoff hierarchy section
    MUST include open questions and uncertainties section
    MUST label requirements as requirements and not mechanisms
    MUST NOT filter out attributes before sending to pipeline
  }

  MUST NOT synthesise implications when utility_tree is None.
    — architectural drivers are read from utility_tree.architectural_drivers;
      without a tree, driver traceability is impossible.

  MUST limit results to MAX_IMPLICATIONS = 20 entries per synthesis call.
    — trim silently; do not raise an error when the LLM returns more.

  MUST return the existing architecture_implications list when the LLM fails.
    — never discard previously synthesised implications on a transient error.

  MUST trace every implication to a specific source_scenario_id.
    — implications without a traceable scenario MUST be rejected or omitted.
}

ASSERT duplicate_submission_prevention {
  The send-to-pipeline UI action MUST set isSubmitting=true on the first click
  and ignore subsequent clicks until navigation completes or an error is returned.

  Every send-to-pipeline HTTP request MUST include an Idempotency-Key header
  generated client-side per click.

  Spring Boot MUST cache the pipeline result keyed by Idempotency-Key for
  5 minutes and return the cached result for duplicate requests.

  WorkshopSession MUST store pipeline_conversation_id and pipeline_sent_at
  to detect server-side duplicates within 60 seconds even without an
  idempotency key.
}

ASSERT scenario_deduplication {
  MUST use deduplicated_scenarios property when building the pipeline formatter
  input — not the raw scenarios list.

  deduplicated_scenarios MUST use content hash of stimulus + artifact +
  response to identify duplicates.

  When duplicates exist, MUST keep the more complete scenario and merge
  exercises_attributes from the duplicate.

  The formatter MUST use writtenScenarioIds to ensure no scenario appears in
  both driver and supporting sections.
}

ASSERT attribute_coverage {
  Every attribute named in any scenario's exercises_attributes list MUST
  appear in the attribute list.

  If an attribute is missing, MUST add it as tentative with scenario evidence
  — it must not be silently absent.

  The infer_attributes_from_scenarios_node MUST run a coverage gap check after
  the LLM produces its attribute list.
}

ASSERT proactive_measure_elicitation {
  MUST include needs_measure scenarios in the workshop_scenarios kwarg
  passed to the generate_questions prompt.
    — generate_response_node MUST pass all WorkshopScenario objects
      as [s.model_dump() for s in state.scenarios] — no filtering.

  MUST NOT filter out needs_measure scenarios from the prompt context.
    — the generate_questions template is responsible for surfacing these
      to the LLM as priority clarification targets.
}

ASSERT canonical_decision_propagation {
  canonical_decisions property MUST handle field name variants
  from the buy_vs_build LLM output:
  component_name, component, capability, name
  recommendation, decision, action
  Only buy and adopt decisions produce canonical constraints.

  MUST log ARCHITECTURE_GEN_AUDIT before every architecture
  generation call showing canonical_decisions count and each
  component/decision pair.

  MUST log WARNING when buy_vs_build_analysis is non-empty
  but canonical_decisions is empty — this indicates a field
  name mismatch.

  The architecture generator prompt MUST include explicit
  excluded_component_patterns for each buy/adopt decision
  so the model has concrete patterns to check against.

  Every generated component MUST have an ownership field
  with value from the defined enum:
  enterprise-built | bought-saas | adopted-platform |
  integration-adapter | governance-service

  Bought capabilities MUST appear as type=external with
  ownership=bought-saas — never as type=service.

  ADL generation MUST receive canonical_decisions as an
  explicit prompt input and MUST generate one ADL block
  per buy/adopt decision in addition to structural blocks.

  Governance scoring MUST apply -3 per sourcing conflict
  (internal component implementing a bought capability)
  and +2 per respected sourcing decision.
}

ASSERT conversation_routing_integrity {
  EVERY SSE event written to an emitter MUST be logged
  with SSE_AUDIT prefix including conversationId, userId,
  eventType, stage, emitterCount, and threadId.

  EVERY SSE event received from the agent MUST be validated
  for conversationId match before forwarding.

  Events with non-matching conversationId MUST be discarded
  with ROUTING_VIOLATION error log — never forwarded.

  PipelineRunService.startRun() MUST check for an existing
  RUNNING pipeline for the conversationId before creating
  a new one — duplicate runs MUST throw
  DuplicatePipelineRunException.

  React store startStream() MUST set conversationId and
  isStreaming in a single atomic update — never in two
  separate set() calls.

  A submit handler MUST check isStreaming before making
  any API call — duplicate submissions MUST be blocked
  client-side before reaching the server.
}

ASSERT adl_minimum_blocks {
  ADL generation MUST produce a minimum of 5 blocks per run.
  Fewer than 3 blocks is a quality failure and MUST log
  a WARNING with the block count.
  The adl_generator prompt MUST include an explicit minimum
  block count instruction of 5.
}

ASSERT canonical_decision_traceability {
  When buy_vs_build_analysis produces buy or adopt decisions,
  architecture_generation MUST log CANONICAL_DECISIONS with
  the decision count and component names.
  Zero canonical decisions MUST log a WARNING.
  buy_vs_build_analysis MUST log its decision count and
  classification breakdown on every run.
}

ASSERT interaction_contract {
  Every interaction object in architecture_design.interactions
  MUST have non-empty, non-undefined protocol and purpose fields.

  Interactions with undefined or empty protocol MUST be
  rejected by _validate_interactions() before being written
  to context.

  Valid protocol values: REST, gRPC, GraphQL, WebSocket, SSE,
  AMQP, Kafka, NATS, SMTP, FTP, SFTP, SDK, webhook,
  database, in-process.

  "undefined", "null", "unknown", and empty strings are
  never valid protocol or purpose values.
}

ASSERT governance_scoring_grounded {
  Governance score MUST be calculated from actual artifact
  counts — ADL blocks, FMEA risks, trade-offs, requirements.

  Score evidence strings MUST be included in the governance
  report — one sentence per dimension stating the count
  that produced the score.

  The same governance score across radically different
  systems is a scoring engine failure. Score variance
  between systems is expected and correct.

  consistency_bonus dimension MUST reflect actual comparison
  between buy_vs_build_analysis decisions and the
  architecture_design components list.
}

ASSERT mermaid_validation {
  Every generated Mermaid source MUST pass _validate_mermaid_syntax
  before being stored in context.

  If validation fails: one repair attempt is made.
  If repair fails: diagram stored with has_syntax_error=True
  and syntax_error_description populated.

  The UI MUST show a meaningful degraded state for diagrams
  with has_syntax_error=True — never a broken render.
  The raw source MUST be shown so the user can see what
  was generated.
}
10. Never commit a .env file containing real credentials.
