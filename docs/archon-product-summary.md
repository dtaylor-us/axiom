# Archon — Architecture Intelligence Platform
## Product Summary and Technical Reference

**Version:** Current (May 2026)
**Classification:** Side project / Enterprise architecture tooling
**Status:** Production-capable, actively developed

---

## Table of Contents

1. [What Archon Is](#what-archon-is)
2. [The Problem It Solves](#the-problem-it-solves)
3. [Core Capabilities](#core-capabilities)
4. [System Architecture](#system-architecture)
5. [The 13-Stage Reasoning Pipeline](#the-13-stage-reasoning-pipeline)
6. [Quality Attribute Workshop](#quality-attribute-workshop)
7. [Architecture Governance](#architecture-governance)
8. [Technology Stack](#technology-stack)
9. [Infrastructure and Deployment](#infrastructure-and-deployment)
10. [Architecture Characteristics](#architecture-characteristics)
11. [ADL Governance Rules](#adl-governance-rules)
12. [Development Journey and Evaluation History](#development-journey-and-evaluation-history)
13. [Current State and Maturity](#current-state-and-maturity)
14. [Local Development Setup](#local-development-setup)

---

## What Archon Is

Archon is an AI-powered architecture governance and reasoning platform. It transforms unstructured requirements — stakeholder conversations, meeting notes, workshop outputs — into structured, defensible architecture packages that can withstand enterprise governance review.

Unlike AI tools that generate diagrams or produce generic technology recommendations, Archon behaves as an architecture review assistant. It challenges requirements, infers architecture characteristics, selects architecture styles with explicit reasoning, generates weakness and risk analysis, produces ADL governance rules, and critiques its own outputs through a dedicated review agent.

The platform is built by a single developer using AI-assisted tooling (GitHub Copilot) and follows the same architecture governance principles it applies to the systems it analyses. It uses the Mark Richards Architecture Definition Language (ADL) specification to produce enforceable governance rules, and grounds its reasoning in Bass, Clements, and Kazman's quality attribute workshop methodology.

**What Archon is not:**
- A diagram generator with an AI wrapper
- A chatbot that describes architecture patterns
- A requirements management system
- A replacement for a human architect

**What Archon is:**
- A requirements intelligence layer that catches weak, missing, and contradictory requirements
- A quality attribute elicitation system following SEI QAW methodology
- A multi-dimensional architecture reasoning engine across style, tradeoffs, risks, tactics, and governance
- An architecture review assistant that challenges its own generated outputs

---

## The Problem It Solves

Architecture decisions fail more from unstated assumptions than from incorrect technology choices. The typical enterprise architecture process has three failure modes:

**Failure mode 1 — Unstructured input.** Requirements arrive as meeting notes, email threads, and workshop outputs. These contain duplicates, contradictions, implied requirements, and missing constraints. Architects synthesise this manually and inconsistently.

**Failure mode 2 — No explicit quality attribute derivation.** Most architecture work skips formal quality attribute elicitation. Architects assume the important characteristics rather than deriving them from evidence. This leads to architectures optimised for the wrong things.

**Failure mode 3 — Unenforced architecture decisions.** Architecture decisions are documented in Confluence pages that go stale. Service boundary rules are agreed verbally and violated quietly. Code reviews catch violations after the fact, not at design time.

Archon addresses all three:

1. The Quality Attribute Workshop elicits and grounds architecture characteristics from stakeholder evidence before any design work begins.
2. The 13-stage pipeline derives architecture decisions from those characteristics with explicit reasoning, scoring, and tradeoff documentation.
3. The ADL generator produces enforceable governance rules that compile to ArchUnit tests and run in CI on every pull request.

---

## Core Capabilities

### Requirements Intelligence
- Parses and structures unstructured requirement inputs
- Detects missing requirements, ambiguities, and hidden assumptions
- Identifies authentication gaps, retention policy absences, observability gaps
- Generates clarification questions with priority ranking
- Distinguishes confirmed facts from inferred assumptions

### Quality Attribute Workshop (QAW)
- Conversational elicitation following SEI QAW methodology (Bass, Clements, Kazman)
- Derives quality attributes from concrete operational scenarios, not keyword matching
- Tracks information gaps with confidence scores and architectural impact ratings
- Generates utility trees with business importance and technical risk scoring
- Produces architecture implications as requirements, not mechanism prescriptions
- Bridges directly to the main pipeline via formatted requirements brief

### Architecture Reasoning Pipeline
- Selects architecture style from Mark Richards' eight-style catalogue with scoring matrix
- Detects characteristic conflicts (e.g. performance vs consistency in event-driven)
- Generates component designs with explicit ownership classification
- Produces interaction contracts with protocol, purpose, sync/async, and failure handling
- Identifies weaknesses with mitigations
- Runs FMEA with severity, occurrence, detection, RPN, and affected components

### Buy vs Build Analysis
- Evaluates components against build, buy, and adopt recommendations
- Produces named product recommendations (Okta, Amazon SNS, Elastic Stack)
- Propagates sourcing decisions as binding constraints to all downstream stages
- Generates ADL rules preventing internal reimplementation of bought capabilities

### ADL Governance Generation
- Produces Architecture Definition Language blocks following Mark Richards' spec
- Each block includes REQUIRES (tooling), DESCRIPTION, PROMPT (Copilot instruction), DEFINE, and ASSERT
- PROMPT field is a ready-to-use Copilot instruction that generates compilable ArchUnit or PyTestArch tests
- Validates that generated ADL only references components present in the architecture model
- Minimum five blocks per run, maximum twelve

### Governance Scoring
- Dynamic score derived from actual pipeline artifact counts (not estimated)
- Five dimensions: requirement coverage, characteristic alignment, trade-off quality, ADL enforceability, risk awareness
- Consistency bonus/penalty for sourcing decision propagation fidelity
- Score evidence strings show the specific counts behind each dimension score
- Deductions for SPOF findings, ADL contradictions, and sourcing conflicts

### Architecture Review Agent
- Separate LangGraph agent that critiques the generated architecture
- Challenges architecture style selection against primary characteristics
- Flags deferred concerns and governance gaps
- Identifies cross-section contradictions (e.g. sourcing says buy but architecture builds)
- Re-iteration gate: if governance score < 70, triggers one targeted repair pass

---

## System Architecture

Archon is a three-service architecture following Mark Richards' service-based pattern. The services are coarse-grained, each owns a full domain, and they communicate via HTTP. The internal structure of each service is modular monolith with domain-partitioned modules and enforced boundaries via ADL rules and ArchUnit tests.

```
┌─────────────────────────────────────────────────────────────┐
│  Browser / archon-ui                                        │
│  React 18 + TypeScript + Vite  ·  port 3000                │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP + SSE streaming
┌────────────────────────▼────────────────────────────────────┐
│  archon-api                                                 │
│  Spring Boot 3.x / Java 21  ·  port 8080                   │
│                                                             │
│  Auth · Conversations · Pipeline runs · Workshop sessions   │
│  SSE bridge · Durable run lifecycle · Password reset        │
│  Idempotency · Rate limiting · Resilience4j circuit breaker │
│                                                             │
│  PostgreSQL (persistence)                                   │
│  Azure Key Vault (secrets)                                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (X-Internal-Secret)
┌────────────────────────▼────────────────────────────────────┐
│  archon-agent                                               │
│  Python 3.11 / FastAPI + LangGraph  ·  port 8001           │
│                                                             │
│  13-stage reasoning pipeline  ·  QAW conversational agent  │
│  Architecture Review Agent  ·  LLM client abstraction      │
│  Context budget management  ·  Structured output schemas   │
│                                                             │
│  Qdrant (vector memory)                                     │
│  Ollama / OpenAI (LLM provider — switchable)               │
└─────────────────────────────────────────────────────────────┘
```

### Service boundaries enforced by ADL

- `archon-api` must not import from openai, langchain4j, or azure.ai.openai
- `archon-agent` must not import from psycopg2 or access PostgreSQL directly
- LLM calls are prohibited in the Spring Boot service — they belong exclusively in the Python agent
- Qdrant client access is restricted to the Python agent

These constraints are enforced by ArchUnit tests (Java) and PyTestArch tests (Python) that run in CI on every pull request.

---

## The 13-Stage Reasoning Pipeline

The pipeline is a LangGraph StateGraph that passes a shared `ArchitectureContext` object through each stage. Every stage emits a `STAGE_COMPLETE` event to the Spring Boot SSE bridge which forwards it to the browser in real time.

| Stage | Name | Model tier | Key output |
|-------|------|-----------|------------|
| 1 | requirement_parsing | Primary | Structured requirements with type classification |
| 2 | requirement_challenge | Primary | Missing requirements, ambiguities, hidden assumptions |
| 3 | scenario_modeling | Primary | Quality attribute scenarios with stimulus/response/measure |
| 4 | characteristic_inference | Primary | Ranked architecture characteristics with confidence |
| 4b | tactics_recommendation | Fast | Tactics from Bass/Clements/Kazman catalog per characteristic |
| 5 | conflict_analysis | Primary | Characteristic tensions with interpretation |
| 6 | architecture_generation | Primary | Style selection, components, interactions with ownership |
| 6b | buy_vs_build_analysis | Primary | Sourcing recommendations with provider names |
| 7 | diagram_generation | Primary | Mermaid diagrams, one LLM call per diagram type |
| 8 | trade_off_analysis | Primary | Explicit tradeoffs with sacrifice and rationale |
| 9 | adl_generation | Primary | 5-12 ADL governance blocks with Copilot prompts |
| 10 | weakness_and_fmea | Primary | Weaknesses then FMEA (sequential — FMEA needs weakness context) |
| 12 | architecture_review | Primary | Governance critique, re-iteration gate if score < 70 |

**Core stages** (abort the run on failure): 1, 2, 4, 6

**Supporting stages** (record a gap and continue): 4b, 6b, 7, 8, 9, 10

**Pipeline resilience mechanisms:**
- One repair attempt per stage on JSON parse or Pydantic validation failure
- Per-type sequential diagram generation — one diagram type failing does not lose others
- `COMPLETED_WITH_GAPS` run status when supporting stages fail
- Durable run lifecycle — runs survive browser disconnects and can be resumed
- SSE keepalive every 15 seconds prevents proxy timeout on long runs

---

## Quality Attribute Workshop

The QAW is a separate conversational module that precedes the main pipeline. It follows the SEI Quality Attribute Workshop method from CMU/SEI-2001-TR-020.

### Workshop graph (LangGraph)

```
analyze_input → identify_gaps → reconcile_gaps → resolve_questions
→ elicit_scenarios → infer_attributes_from_scenarios → consolidate
→ generate_utility_tree → synthesise_implications → check_transition
→ generate_response
```

### Key design decisions

**Scenarios are the primary artifact.** Quality attributes are classification labels derived from scenarios, not the other way round. The workshop asks stakeholders to describe failure scenarios and operational events. Attributes emerge from those scenarios automatically.

**Gaps are confidence-scored, not boolean.** Each information gap has a `resolution_confidence` float (0.0-1.0) that increases as evidence accumulates. A gap is considered resolved when confidence exceeds its threshold (0.9 for critical gaps, 0.75 for high, 0.6 for medium). This prevents the system from asking questions the user already answered.

**Attribute consolidation with a hard cap.** After every generation pass, the `ConsolidationEngine` normalises attribute names against a canonical taxonomy, merges semantic duplicates, separates non-QA concerns, and caps the list at 12 attributes. This prevents the 84-attribute explosion observed in early iterations.

**Ask before assert.** The system never imposes quality attributes. It identifies information gaps first, asks targeted questions, and only derives attributes when there is sufficient evidence. Attributes without scenario evidence are marked tentative.

**User-controlled generation.** The user can request attribute generation at any point after the first turn. A readiness assessment shows what the current evidence will and will not support before committing. The session remains open after generation — the user can continue refining.

### Utility tree generation

When the session has 5+ scenarios across 3+ attributes, the workshop generates a SEI QAW utility tree. Each scenario is scored by business importance (H/M/L) and technical risk (H/M/L). Scenarios scored (H,H) are architectural drivers — the decisions that most constrain the architecture.

### Architecture implications

The `ImplicationSynthesiser` derives architectural requirements from driver scenarios. These are requirements, not mechanisms. "Because the WAN degradation scenario requires continued robot coordination without cloud connectivity, local orchestration must remain fully operational during disconnection periods of up to 15 minutes" — not "the architecture must include a consensus protocol."

Prohibited mechanism terms are enforced by a validator and a CI grep check. Any implication containing "async worker pool", "consensus protocol", "circuit breaker", or similar mechanism names logs a warning.

### Send to pipeline

The workshop output is formatted as a natural language requirements brief and submitted to the main pipeline as a user message. The pipeline treats workshop output as user input, preserving its ability to challenge and refine the elicited attributes through its own stages.

---

## Architecture Governance

### ADL — Architecture Definition Language

Archon implements Mark Richards' ADL specification. Each ADL block has:

```
REQUIRES [tooling — ArchUnit, PyTestArch, Semgrep, or grep]
DESCRIPTION [human-readable rule label]
PROMPT [Copilot instruction that generates the enforcement test]
DEFINE [component/system/library declarations]
ASSERT [the actual constraint]
```

The PROMPT field is the key innovation. A developer pastes the PROMPT field into GitHub Copilot and receives a compilable ArchUnit or PyTestArch test. No knowledge of ArchUnit syntax is required. The ADL block documents the intent; Copilot writes the enforcement.

**Currently 44 ADL blocks** covering:
- Service boundary isolation (Java and Python)
- LLM call prohibition in the Spring Boot service
- Database access boundaries
- Token storage prohibition
- Scenario-first graph ordering
- Scenario completeness computed not LLM-assigned
- No single gap completion percentage
- Governance score grounded in artifacts not estimates
- Conversation routing integrity
- Measure category validation
- Implication mechanism prohibition
- Structured output schema enforcement
- One repair attempt per stage
- Per-type diagram generation
- Canonical decision propagation
- Workshop ask-before-assert principle

### Governance scoring

Five dimensions, 0-20 each, plus a consistency bonus of -10 to +10:

| Dimension | What it measures |
|-----------|-----------------|
| Requirement coverage | Requirements traceable to specific components |
| Characteristic alignment | Primary characteristics with dedicated architectural design |
| Trade-off quality | Tradeoffs with specific rationale, named sacrifice |
| ADL enforceability | ADL blocks with testable ASSERT conditions and tooling |
| Risk awareness | FMEA risks with mitigations and RPN scoring |
| Consistency bonus | Buy/adopt decisions reflected as external components |

Score evidence strings are mandatory — each dimension must state the count that produced the score ("3 of 5 primary characteristics have dedicated design"). A score of 65 across radically different systems is a scoring engine failure.

---

## Technology Stack

### archon-api (Spring Boot)

| Component | Technology |
|-----------|-----------|
| Framework | Spring Boot 3.3.4 / Java 21 |
| Auth | JWT (custom JwtAuthFilter) |
| Persistence | Spring Data JPA + Hibernate 6 |
| Database | PostgreSQL 16 |
| Migrations | Flyway (19 migrations) |
| HTTP client | Spring WebFlux WebClient |
| Resilience | Resilience4j (circuit breaker, rate limiter) |
| Caching | Caffeine (idempotency keys) |
| Observability | OpenTelemetry + Micrometer + Prometheus |
| Email | Spring Mail (JavaMailSender, any SMTP provider) |
| Build | Maven |
| Tests | JUnit 5 + MockMvc + Testcontainers |
| Governance | ArchUnit |

### archon-agent (FastAPI)

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI + Uvicorn |
| Orchestration | LangGraph (StateGraph) |
| LLM (production) | OpenAI gpt-4o via openai SDK |
| LLM (local dev) | Ollama (qwen3:14b primary, qwen3:8b fast) |
| Structured output | Provider-native JSON schema (Ollama format param, OpenAI json_schema) |
| Vector memory | Qdrant |
| Observability | OpenTelemetry |
| Template engine | Jinja2 (.j2 prompt files) |
| Tests | pytest + PyTestArch |
| Governance | PyTestArch |

### archon-ui (React)

| Component | Technology |
|-----------|-----------|
| Framework | React 18 + TypeScript |
| Build | Vite |
| State | Zustand |
| HTTP | Fetch API + SSE EventSource |
| Diagrams | Mermaid.js |
| Charts | Recharts |
| Styles | CSS variables (dark theme) |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Container runtime | Docker Desktop / Docker Compose (local) |
| Cloud platform | Azure AKS (production) |
| IaC | Terraform (Azure provider) |
| Container registry | Azure Container Registry |
| Secrets | Azure Key Vault with CSI driver |
| DNS/TLS | Let's Encrypt via cert-manager (HTTP-01 challenge) |
| Ingress | nginx ingress controller |
| CI/CD | GitHub Actions |
| Deployment | Helm (--atomic rollback) |
| Monitoring | Prometheus + Grafana |
| Tracing | Jaeger (OTLP gRPC on port 4317) |
| Local email | Mailhog (development SMTP capture) |

---

## Architecture Characteristics

Derived from the system's own requirements and design decisions, using the same methodology Archon applies to its users:

**Primary characteristics (drive architecture decisions):**
- **Reliability** — a 13-stage pipeline run taking 5-15 minutes cannot fail mid-way. Drives: durable run lifecycle, COMPLETED_WITH_GAPS status, SSE keepalive, repair attempts.
- **Correctness** — an architecture assistant producing wrong answers is actively harmful. Drives: Richards 8-style scoring with veto rules, tactics catalog with minimum field length validation, ADL spec enforcement, review agent.
- **Data integrity** — a governance score produced with failed review sub-stages is a data integrity violation. Drives: review health tracking, governance_score_confidence field, FMEA/weakness ordering.
- **Auditability** — architects need traceable reasoning chains. Drives: 13 STAGE_COMPLETE events, append-only pipeline_events table, ADL blocks with REQUIRES/DESCRIPTION/PROMPT.
- **Modifiability** — stages inserted at 4b and 6b without touching existing stages. Drives: tool registry, LLM provider abstraction, Jinja2 prompt templates as files.

**Secondary characteristics:**
- Observability, Testability, Security, Deployability, Cost awareness, Recoverability

**Implicit characteristics:**
- Simplicity (three services maximum — one developer), Evolvability, Feasibility

**Key characteristic tensions:**
- Correctness vs Reliability: complex prompts produce better output but are more brittle
- Auditability vs Cost awareness: full event logging grows storage with every run
- Modifiability vs Correctness: prompt changes can silently degrade output quality
- Simplicity vs Reliability: Phase 2 contract hardening adds complexity

---

## ADL Governance Rules (Summary)

The full ADL.md contains 44 blocks. Key rules by category:

**Service isolation (Hard enforcement):**
- API service has no dependency on LLM libraries (OpenAI, LangChain, Azure AI)
- Agent service has no dependency on PostgreSQL or psycopg2
- Workshop module has no dependency on pipeline or tools domains

**LLM output contract (Hard enforcement):**
- Structured output schema enforcement — every LLM call passes an output_schema
- One repair attempt per stage — no silent swallowing, no unlimited retries
- Diagram generation per-type sequential — batch generation permanently retired

**Workshop methodology (Hard enforcement):**
- Scenario-first graph ordering — elicit_scenarios before infer_attributes
- Scenario completeness computed not LLM-assigned — model cannot self-report "complete"
- No single gap completion percentage — multi-dimensional progress model only
- Workshop ask-before-assert — gaps identified before attributes derived

**Governance integrity (Hard enforcement):**
- No mechanism implications — prompts must state requirements not solutions
- Governance score grounded in artifacts — estimated scores prohibited
- Canonical decision propagation — buy/adopt decisions must reach all downstream stages
- Interaction contracts — undefined protocol/purpose values prohibited

**Testing (Hard enforcement):**
- 80% coverage minimum for both services
- All seam tests must pass — UI stream event to run event, stage output to artifact

---

## Development Journey and Evaluation History

Archon was developed through nine documented QA evaluation sessions, each producing a report that drove the next iteration. The trajectory shows a clear progression:

| Session | Status | Key capability |
|---------|--------|---------------|
| V1 | Questionnaire engine | Attribute elicitation, basic extraction |
| V2 | Over-corrected | 84 attributes → 1 (deduplication too aggressive) |
| V3 | Scenario extraction | Scenario-driven facilitation emerging |
| V4 | Scenario-centric | 12 structured scenarios, attribute-scenario traceability |
| V5 | Architecture reasoning | Measurable operational targets, tradeoff hierarchy |
| V6 | Multi-dimensional reasoning | FMEA, weakness, tactics, sourcing simultaneously |
| V7 | Architecture governance | Assumption challenges, style selection challenges |
| V8 | Architecture critique | Critiquing architectures, not just generating them |
| V9 | End-to-end pipeline | Full workshop-to-architecture-to-ADL workflow confirmed |

**V9 final evaluation summary:**
- Architecture reasoning: Strong
- Governance review: Major improvement
- Requirement analysis: Strong
- Tradeoff analysis: Excellent
- Weakness analysis: Strong
- FMEA quality: Strong
- Architecture consistency: Improving
- Diagram stability: Weak (rendering isolation needed)
- Pipeline integrity: Improving (conversation routing fixes applied)
- Governance explainability: Moderate
- ADL governance depth: Emerging
- Overall platform maturity: Rapidly increasing

The reviewer's final assessment: "Archon is no longer primarily generating architectures. It is critiquing architectures. That is a much more advanced and valuable capability."

---

## Current State and Maturity

### What is working well

- Full end-to-end pipeline from unstructured requirements to governance package
- Quality Attribute Workshop with scenario elicitation and utility tree generation
- Architecture style selection with evidence-based scoring and veto rules
- Buy-vs-build with named product recommendations and binding constraint propagation
- FMEA with severity, occurrence, detection, RPN, and component-level mitigations
- Weakness detection with realistic, architecture-aware findings
- Tradeoff analysis with explicit sacrifice documentation
- ADL generation with Copilot-ready enforcement prompts
- Governance scoring with dimension breakdown and score evidence
- Durable run lifecycle — pipeline runs survive browser disconnects
- Provider switching — one env var toggles between Ollama (local) and OpenAI (production)

### Known limitations and active work

- Mermaid diagram rendering needs isolation boundaries (per-diagram error containment)
- Conversation routing has occasional cross-session contamination (SseEmitterRegistry fixes applied, monitoring in place)
- ADL block count regressed to single block (git history investigation underway)
- Governance score can be optimistic on systems with multiple unresolved concerns
- Sourcing-to-architecture propagation occasionally produces custom services for bought capabilities

### Architecture decisions made intentionally

- Three services maximum — no message broker, no microservices decomposition
- StatefulStateGraph (LangGraph) with shared ArchitectureContext — no distributed state
- Prompt templates as Jinja2 files — tunable without code deployment
- LLM provider abstraction — test locally with Ollama, deploy with OpenAI
- Richards ADL spec — generates tests via Copilot, no custom tooling needed

---

## Local Development Setup

### Prerequisites

- Docker Desktop (macOS: **do not run Ollama in Docker** — use native install)
- Java 21 (via SDKMAN)
- Node.js 20 (via nvm)
- Python 3.11 (via pyenv or conda)
- Homebrew (macOS)

### First-time setup (macOS Apple Silicon)

```bash
# 1. Install Ollama natively — critical for GPU acceleration
#    Docker Desktop cannot access Apple Silicon GPU (Metal)
#    Running Ollama in Docker means CPU-only inference at 8-12 tok/sec
#    Native Ollama uses Metal at 40-60 tok/sec
brew install ollama
brew services start ollama
ollama pull qwen3:14b   # primary model (9.3 GB)
ollama pull qwen3:8b    # fast model (5.2 GB)

# 2. Verify GPU is active
ollama run qwen3:8b "say hello" --verbose 2>&1 | grep "eval rate"
# Should show 40+ tok/sec. Below 15 = still on CPU.

# 3. Configure environment
cp .env.example .env
# Default OLLAMA_BASE_URL=http://host.docker.internal:11434 is correct
# The agent container reaches native Ollama via host.docker.internal

# 4. Start the stack (Ollama is NOT in docker-compose)
docker compose up -d

# 5. Open the application
open http://localhost:3000
```

### Hardware tiers (Apple Silicon)

| Mac model | Memory | Primary model | Fast model | Pipeline time |
|-----------|--------|---------------|------------|---------------|
| M1/M2 base | 8 GB | qwen3:8b | qwen3:8b | 20-30 min |
| M1 Pro/M2 Pro | 16 GB | qwen3:14b | qwen3:8b | 10-15 min ✓ |
| M2 Max/M3 Max | 32-64 GB | qwen3:32b | qwen3:14b | 8-12 min |
| M5 Pro | 48 GB | qwen3:14b | qwen3:8b | 8-12 min |

### Switching to OpenAI

```bash
# Edit .env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o

# Restart agent only
docker compose restart agent
```

### Services when running locally

| Service | URL | Purpose |
|---------|-----|---------|
| UI | http://localhost:3000 | Main application |
| API | http://localhost:8080 | Spring Boot REST API |
| Agent | http://localhost:8001 | Python FastAPI agent |
| Qdrant | http://localhost:6333 | Vector database UI |
| Mailhog | http://localhost:8025 | Email capture (password reset testing) |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3001 | Dashboards |
| Jaeger | http://localhost:16686 | Distributed tracing |
| PostgreSQL | localhost:5432 | Primary database |

---

## Appendix A — Pipeline Event Reference

Each SSE event from the agent has this structure:

```json
{
  "type": "STAGE_START | STAGE_COMPLETE | ERROR | COMPLETE",
  "stage": "requirement_parsing | ...",
  "conversationId": "uuid",
  "payload": { ... stage-specific data ... }
}
```

The `COMPLETE` event payload includes:
- Final governance score with dimension breakdown
- All generated artifacts
- Pipeline gaps (stages that completed with gaps)
- has_gaps boolean
- Estimated cost (when using OpenAI)

---

## Appendix B — Key Data Models

**ArchitectureContext** — the shared pipeline state object, passed through all 13 stages:
- parsed_requirements, challenged_requirements
- scenarios, characteristics, conflicts
- architecture_style, architecture_design (components + interactions)
- buy_vs_build_analysis, canonical_decisions (computed property)
- diagrams, trade_offs, adl_blocks
- weaknesses, fmea_risks
- governance_score, review_findings
- pipeline_gaps, has_gaps

**WorkshopContext** — the QAW session state:
- scenarios (primary artifacts), attributes (derived from scenarios)
- gaps (confidence-scored), open_gaps, filled_gaps
- utility_tree, architecture_implications
- workshop_phase (10 QAW phases)
- generation_count, attributes_stale

**PipelineRun** — durable run record in PostgreSQL:
- status: RUNNING | COMPLETED | COMPLETED_WITH_GAPS | FAILED
- pipeline_events (append-only event log)
- governance_score, governance_confidence
- total_tokens, estimated_cost_usd

---

*This document reflects Archon's state as of May 2026. The platform is under active development.*
