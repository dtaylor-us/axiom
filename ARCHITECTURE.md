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
  RESPONSIBILITY: "AI-powered architecture governance and design assistant"
  SERVICES: [ai-architect-api, ai-architect-agent, ai-architect-ui]
  DATABASES: [PostgreSQL, Qdrant]
  COMMUNICATION: [HTTP/SSE between client and api, HTTP/NDJSON between api and agent]
  DEPLOYMENT: Docker Compose (local), AKS (production)
}


---

## SERVICE: ai-architect-api (Spring Boot)

DEFINE service ai-architect-api {
  LANGUAGE: Java 21
  FRAMEWORK: Spring Boot 3.3.4
  RESPONSIBILITY: "API gateway — auth, session management, SSE streaming, agent bridge"
  OWNS: [Conversation, Message, ConversationStatus, MessageRole, ArchitectureOutput]
  DOES_NOT_OWN: [ArchitectureContext, pipeline logic, LLM calls, tool execution]
  EXPOSES: [
    POST /api/v1/chat/stream,
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
  CALLS: [ai-architect-agent via AgentHttpClient]
  ROOT_PACKAGE: com.aiarchitect.api
}

ASSERT ai-architect-api {
  MUST use Flyway for all schema changes
    — ddl-auto MUST be "validate", never "create", "update", or "create-drop"

  MUST NOT contain LLM API calls
    — no openai, azure-openai, langchain, or llm client dependencies in pom.xml

  MUST NOT contain pipeline logic
    — no stage orchestration, no tool invocation, no ArchitectureContext manipulation

  MUST use WebClient (not RestTemplate) for all HTTP calls to ai-architect-agent
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
    — AgentHttpClient MUST set this header on every request to ai-architect-agent

  MUST NOT expose internal exceptions to API consumers
    — AgentCommunicationException MUST be caught and mapped to a safe error response

  MUST limit conversation history sent to agent
    — getRecentMessages() MUST be called with limit <= 20 before building AgentRequest
}

REQUIRE ai-architect-api {
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

## SERVICE: ai-architect-agent (Python / FastAPI)

DEFINE service ai-architect-agent {
  LANGUAGE: Python 3.11
  FRAMEWORK: FastAPI + LangGraph (Phase 2+)
  RESPONSIBILITY: "LLM orchestration — pipeline execution, tool dispatch, streaming"
  OWNS: [ArchitectureContext, pipeline stages, tool registry, prompt templates]
  DOES_NOT_OWN: [Conversation, Message, session state, JWT auth]
  EXPOSES: [POST /agent/stream, GET /health]
  ROOT_MODULE: app
}

ASSERT ai-architect-agent {
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

  MUST NOT call Spring Boot or any ai-architect-api endpoint
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

REQUIRE ai-architect-agent {
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

## SERVICE: ai-architect-ui (React / Vite)

DEFINE service ai-architect-ui {
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
  ROOT_DIR: ai-architect-ui/src
}

ASSERT ai-architect-ui {
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

REQUIRE ai-architect-ui {
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
  USED_BY: [ai-architect-api only]
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
  USED_BY: [ai-architect-agent only]
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
  MUST NOT allow ai-architect-agent to connect to PostgreSQL directly
    — agent has no PostgreSQL connection string in its environment

  MUST NOT allow ai-architect-api to connect to Qdrant directly
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
  CHART: helm/ai-architect (Helm v3)
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
  MUST deploy to AKS via Helm chart in helm/ai-architect/
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

2. Place new Java classes in the correct package under com.aiarchitect.api.
   Never create classes outside the root package.

3. Never write raw SQL outside of Flyway migration files.
   JPA repositories handle all queries; JPQL is allowed in @Query annotations.

4. Never add spring.jpa.hibernate.ddl-auto values other than "validate".

5. Never use RestTemplate. Always use WebClient for HTTP calls.

6. Never call the OpenAI or Azure OpenAI API from ai-architect-api.
   All LLM calls belong exclusively in ai-architect-agent.

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
10. Never commit a .env file containing real credentials.