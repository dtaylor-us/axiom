# Axiom — Architecture Intelligence Platform

Axiom is a four-pillar AI-powered platform that helps software teams design, refine, and review system architectures through an interactive conversational interface.

The platform is live at: **<https://axiom-dev.eastus2.cloudapp.azure.com/>**

---

## Platform Overview

Axiom is organised as a gateway plus four active pillars. Each pillar is a pair of services: a Spring Boot API and a Python/FastAPI agent.

```
┌──────────────────────────────────────────────────────────────────┐
│                        axiom-ui  :3000                           │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼──────────────────────────────────────┐
│               axiom-api  :8080  (platform gateway)               │
│          JWT validation · pillar routing · health aggregation    │
└──────────┬──────────────┬───────────────┬──────────────┬─────────┘
           │              │               │              │
  ┌────────▼───────┐ ┌────▼─────────┐ ┌───▼───────┐ ┌───▼────────┐
  │  archon-api    │ │specweaver-api│ │ lens-api  │ │memoria-api │
  │  :8081         │ │ :8082        │ │ :8083     │ │ :8084      │
  └────────┬───────┘ └────┬─────────┘ └───┬───────┘ └───┬────────┘
           │              │               │             │
  ┌────────▼───────┐ ┌────▼─────────┐ ┌───▼───────┐ ┌───▼────────┐
  │ archon-agent   │ │specweaver-   │ │lens-agent │ │memoria-    │
  │  :8001         │ │agent :8085   │ │ :8086     │ │agent :8087 │
  └────────────────┘ └──────────────┘ └───────────┘ └────────────┘
```

| Service | Stack | Port | Responsibility |
|---------|-------|------|----------------|
| **axiom-ui** | React 18 + TypeScript + Vite | 3000 | Unified UI shell — all pillars |
| **axiom-api** | Spring Boot 3.x / Java 21 | 8080 | Platform gateway — auth, JWT validation, pillar routing |
| **archon-api** | Spring Boot 3.x / Java 21 | 8081 | Architecture reasoning — conversation management, run state |
| **archon-agent** | FastAPI + LangGraph / Python 3.11 | 8001 | 14-stage architecture reasoning pipeline |
| **specweaver-api** | Spring Boot 3.x / Java 21 | 8082 | Requirements intelligence — session management, document ingestion |
| **specweaver-agent** | FastAPI + LangGraph / Python 3.11 | 8085 | Requirements extraction, consolidation, gap analysis, conflict detection |
| **lens-api** | Spring Boot 3.x / Java 21 | 8083 | Architecture review — session management, gap elicitation, report storage |
| **lens-agent** | FastAPI + LangGraph / Python 3.11 | 8086 | 10-stage architecture review pipeline |
| **memoria-api** | Spring Boot 3.x / Java 21 | 8084 | Project memory — project management, session linking, ADR register, context assembly |
| **memoria-agent** | FastAPI + LangGraph / Python 3.11 | 8087 | Session distillation, fact extraction, conflict detection, embedding generation |

---

## Pillars

### Archon — Architecture Reasoning

Given a set of requirements, Archon runs a 14-stage pipeline that parses requirements, challenges assumptions, models scenarios, infers quality characteristics, recommends architecture tactics, resolves conflicts, generates architecture designs with diagrams, performs trade-off and ADL analysis, runs FMEA, and produces an automated governance review — all streamed in real time.

### SpecWeaver — Requirements Intelligence

Accepts messy stakeholder input (meeting notes, emails, PDFs, informal bullets) and transforms it into a structured, traceable, architecture-ready requirements package. Extracts, deduplicates, classifies, detects gaps and conflicts, scores readiness, and generates a brief for Archon.

### Lens — Architecture Review Intelligence

Evaluates existing architectures against the Azure Well-Architected Framework (five pillars), SEI ATAM, SEI quality attribute principles, and structural health principles. Conducts iterative gap elicitation — asking targeted questions until sufficient information is gathered — then generates a structured review report with a risk register and prioritised recommendations. The system never blocks the user: unresolved gaps become findings in the report.

### Memoria — Project Memory

Maintains a persistent, structured knowledge store for each project.
Draws from SpecWeaver sessions (requirements, gaps), Archon conversations
(architecture decisions, trade-offs, risks), and Lens reviews (WAF scores,
ATAM findings, risk register). Stores knowledge in three tiers: working
memory (in-session, ephemeral), episodic memory (TTL-aware facts with
vector search), and semantic memory (ADR register, never expires, human-confirmed).

Pillar APIs call memoria-api at session start to inject relevant project context
and at session close to trigger distillation of the session into memory entries.
Stale, superseded, and archived entries are never injected into LLM context —
only active decisions and requirements flow into the context package.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) v2+
- An **OpenAI API key** (or Ollama running locally)

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/dtaylor-us/axiom.git
cd axiom
cp .env.example .env
```

Edit `.env` and add your LLM credentials:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 2. Choose your startup mode

Axiom supports five startup modes depending on what you are working on:

#### Archon only (fastest — default)

```bash
docker compose up --build
```

Access at: <http://localhost:3000>

#### SpecWeaver pillar added

```bash
docker compose --profile specweaver up --build
```

#### Lens pillar added

```bash
docker compose --profile lens up --build
```

Adds: `lens-api`, `lens-agent`

#### Memoria pillar added

```bash
docker compose --profile memoria up --build
```

Adds: `memoria-api`, `memoria-agent`

#### Full Axiom platform (all pillars + gateway)

```bash
docker compose --profile platform up --build
```

Adds: `axiom-api` (gateway), `specweaver-api`, `specweaver-agent`,
`lens-api`, `lens-agent`, `memoria-api`, `memoria-agent`, `minio`

Access at: <http://localhost:3000> (traffic routes through axiom-api on :8080)

> **Note:** In `platform` mode the gateway validates JWTs and routes all
> `/api/v1/archon/**`, `/api/v1/specweaver/**`, `/api/v1/lens/**`,
> and `/api/v1/memoria/**`
> traffic. In the other modes each pillar API handles auth directly
> (`AXIOM_GATEWAY_BYPASS=true`).

---

## Archon Pipeline Stages

The Archon agent runs a 14-stage pipeline on every request:

1. **Requirement Parsing** — extract structured requirements from natural language
2. **Requirement Challenge** — question assumptions and identify gaps
3. **Scenario Modeling** — generate usage and failure scenarios
4. **Characteristic Inference** — reason about quality attributes
5. **Tactics Recommendation** — BCK catalog tactics per quality attribute
6. **Conflict Analysis** — detect trade-offs between competing characteristics
7. **Architecture Generation** — produce architecture design with component descriptions
8. **Buy vs Build Analysis** — named product recommendations per component
9. **Diagram Generation** — C4 and sequence diagrams in Mermaid
10. **Trade-off Analysis** — structured trade-off record
11. **ADL Generation** — Architecture Definition Language rules and fitness functions
12. **Weakness Analysis** — identify architectural weaknesses
13. **FMEA Analysis** — failure mode and effects analysis with Risk Priority Numbers
14. **Architecture Review** — governance scoring across five dimensions (0–100)

## Lens Pipeline Stages

The Lens agent runs a 10-stage review pipeline:

1. **Evidence Parsing** — parse submitted architecture into structured representation
2. **Azure WAF Analysis** — evaluate against five Azure Well-Architected pillars
3. **ATAM Analysis** — SEI quality attribute scenarios, sensitivity points, tradeoffs, risks
4. **SEI Analysis** — modifiability, performance, availability, security, integrability
5. **Structural Analysis** — coupling, cohesion, dependency direction, boundary clarity
6. **Risk Identification** — unified risk register (max 20 risks)
7. **Recommendation Generation** — prioritised actionable recommendations (max 15)
8. **Executive Summary** — 3-5 paragraph summary with overall rating
9. **Report Assembly** — final structured review report
10. **Review Complete** — emit COMPLETE event

---

## Development Agent Workflow

This project uses a three-agent development workflow:

| Agent | Where | Best for |
|-------|-------|----------|
| **Claude** | claude.ai / Claude Desktop | Architecture, planning, debugging, cross-service decisions |
| **Copilot** | GitHub Issues → PRs | Async background implementation, Playwright QA |
| **Codex** | Terminal (`codex`) | Local interactive work, when Copilot quota is low |

See **[docs/AGENTS.md](docs/AGENTS.md)** for the full agent workflow guide including:
- How to create agent-ready GitHub issues
- How to run Playwright QA sessions via Copilot
- How to switch between agents when quota runs low
- Claude Desktop MCP server configuration
- Token conservation strategy

---

## Architecture Governance

This project uses [ARCHITECTURE.md](ARCHITECTURE.md) and [ADL.md](ADL.md) as
authoritative governance documents. All contributions must conform to the rules
defined there. Key invariants:

- **Two services per pillar** — one Spring Boot API, one FastAPI agent. No exceptions.
- **No LLM calls in API services** — all LLM interaction lives in agent services.
- **No PostgreSQL access in agent services** — all persistence belongs in API services.
- **JWT validation in axiom-api only** — pillar APIs trust the `X-Axiom-User-Id` header.
- **No cross-pillar imports** — pillars communicate via HTTP through axiom-api only.
- **All external traffic through axiom-api** — in production and platform mode.
- **Flyway only** — `ddl-auto` is always `validate`.
- **Key Vault CSI for all secrets** — never Terraform-managed secret values in production.

See [ADL.md](ADL.md) for executable fitness functions for each rule.

---

## Project Structure

```
axiom/
├── docker-compose.yml          # Full stack — use profiles to select pillars
├── .env.example                # Environment template
├── ARCHITECTURE.md             # Platform architecture governance
├── ADL.md                      # Architecture Definition Language rules
│
├── axiom-ui/                   # React 18 + TypeScript UI shell
├── axiom-api/                  # Spring Boot platform gateway
│
├── archon-api/                 # Spring Boot — Archon pillar API
├── archon-agent/               # FastAPI + LangGraph — Archon pipeline
│
├── specweaver-api/             # Spring Boot — SpecWeaver pillar API
├── specweaver-agent/           # FastAPI + LangGraph — SpecWeaver pipeline
│
├── lens-api/                   # Spring Boot — Lens pillar API
├── lens-agent/                 # FastAPI + LangGraph — Lens pipeline
│
├── memoria-api/                # Spring Boot — Memoria pillar API
├── memoria-agent/              # FastAPI + LangGraph — Memoria distillation pipeline
│
├── helm/                       # Helm chart for AKS deployment
├── terraform/                  # Azure infrastructure
├── observability/              # Prometheus, Grafana, Jaeger config
└── docs/                       # Extended documentation
    ├── AGENTS.md               # Multi-agent development workflow guide
    ├── DEPLOYMENT.md           # Production deployment guide
    ├── RUNNING.md              # Local development guide
    └── SUPPORT.md              # Troubleshooting guide
```

## License

See [LICENSE](LICENSE) for details.
