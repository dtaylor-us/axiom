# Archon

An AI-powered architecture governance and design assistant that helps software teams generate, evaluate, and refine system architectures through an interactive conversational interface.

Given a set of requirements, the assistant runs a multi-stage pipeline that parses requirements, challenges assumptions, models scenarios, infers quality characteristics, detects conflicts, generates architecture designs with diagrams, and performs automated review — all streamed back in real time.

## Deployed Instance

The current development deployment is live at:

**<https://axiom-dev.eastus2.cloudapp.azure.com/>**

---

## Architecture Overview

The system is composed of two services, two databases, and a Docker Compose orchestration layer:

```
┌────────────┐   SSE (text/event-stream)   ┌──────────────────┐   NDJSON   ┌─────────────────────┐
│   Client   │ ◄──────────────────────────► │  archon-api │ ─────────►│  archon-agent  │
│            │   POST /api/v1/chat/stream   │  (Spring Boot)    │           │  (FastAPI/LangGraph) │
└────────────┘                              └────────┬─────────┘           └──────────┬──────────┘
                                                     │                                │
                                              ┌──────▼──────┐                 ┌───────▼───────┐
                                              │  PostgreSQL  │                │    Qdrant     │
                                              │  (sessions)  │                │  (vectors)    │
                                              └─────────────┘                └───────────────┘
```

| Service | Language | Framework | Port | Responsibility |
|---|---|---|---|---|
| **archon-api** | Java 21 | Spring Boot 3.3.4 | 8080 | API gateway — auth, session management, SSE streaming, agent bridge |
| **archon-agent** | Python 3.11 | FastAPI + LangGraph | 8001 | LLM orchestration — pipeline execution, tool dispatch, streaming |

### Pipeline Stages

The agent runs an 11-stage architecture pipeline on every request:

1. **Requirement Parsing** — extract structured requirements from natural language
2. **Requirement Challenge** — question assumptions and identify gaps
3. **Scenario Modeling** — generate usage and failure scenarios
4. **Characteristic Inference** — reason about quality attributes (scalability, security, etc.)
5. **Conflict Analysis** — detect trade-offs between competing characteristics
6. **Architecture Generation** — produce architecture design with component descriptions
7. **Diagram Generation** — create visual architecture diagrams
8. **ADL Generation** — produce Architecture Definition Language output
9. **Weakness Analysis** — identify architectural weaknesses *(parallel with 10)*
10. **FMEA Analysis** — failure mode and effects analysis *(parallel with 9)*
11. **Architecture Review** — automated governance review with optional re-iteration

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) v2+
- An **OpenAI API key** or **Azure OpenAI** deployment

## Quick Start

### 1. Clone and configure

```bash
git clone <repository-url>
cd axiom
cp .env.example .env
```

Edit `.env` and add your LLM credentials:

```dotenv
# Choose provider: "openai" or "ollama"
LLM_PROVIDER=openai

# OpenAI
OPENAI_API_KEY=sk-...
```

### 2. Start all services

```bash
docker compose up --build
```

This starts four containers:

| Container | Image | Purpose |
|---|---|---|
| `archon-postgres` | `postgres:16-alpine` | Conversation & message persistence |
| `archon-qdrant` | `qdrant/qdrant:v1.13.2` | Vector memory for architecture patterns |
| `archon-agent` | Built from `archon-agent/` | LLM pipeline service |
| `archon-api` | Built from `archon-api/` | REST/SSE API gateway |

### 3. Send a request

```bash
curl -N http://localhost:8080/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Design a payment processing system with Stripe integration"}'
```

The response streams back as Server-Sent Events with stage progress and architecture output.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/chat/stream` | Stream an architecture conversation (SSE) |
| `GET` | `/api/v1/sessions/{id}/messages` | Retrieve conversation history |
| `GET` | `/api/v1/sessions/{id}/architecture` | Get generated architecture output |
| `GET` | `/api/v1/sessions/{id}/diagram` | Get generated architecture diagram |
| `GET` | `/actuator/health` | API health check |

## Environment Variables

### Required

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `openai` or `ollama` |
| `OPENAI_API_KEY` | OpenAI API key (when `LLM_PROVIDER=openai`) |

### Optional

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `localdev` | PostgreSQL password |
| `INTERNAL_SECRET` | `dev-secret-change-in-prod` | Service-to-service auth secret |
| `JWT_SECRET` | `dev-jwt-secret-minimum-32-chars-here` | JWT signing secret |
| `LOG_LEVEL` | `INFO` | Agent log level |

## Development

### Agent (Python)

```bash
cd archon-agent
python -m venv .venv && source .venv/bin/activate
pip install uv && uv pip install -e ".[dev]"

# Run tests
pytest

# Run with auto-reload (requires Qdrant running)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### API (Java)

```bash
cd archon-api

# Run tests (requires Docker for Testcontainers)
./mvnw test

# Run locally (requires PostgreSQL + Agent running)
./mvnw spring-boot:run -Dspring-boot.run.profiles=local
```

### Hot Reload (Docker)

The `docker-compose.override.yml` mounts the agent source directory and enables uvicorn `--reload` for live development:

```bash
docker compose up --build
# Edit files in archon-agent/ — changes reflect immediately
```

## Testing

### Agent

```bash
cd archon-agent
pytest                     # all tests
pytest tests/unit/         # unit tests only
pytest --cov=app           # with coverage (80% minimum enforced)
```

### API

```bash
cd archon-api
./mvnw test                # unit + integration tests (Testcontainers)
./mvnw verify              # includes JaCoCo coverage check (80% line coverage)
```

## Project Structure

```
axiom/
├── docker-compose.yml              # Full stack orchestration
├── docker-compose.override.yml     # Dev overrides (hot reload)
├── .env.example                    # Environment template
├── ARCHITECTURE.md                 # Architecture governance rules
│
├── archon-api/               # Java/Spring Boot API gateway
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/
│       ├── main/java/com/aiarchitect/api/
│       │   ├── api/                # REST controllers
│       │   ├── domain/model/       # JPA entities
│       │   ├── dto/                # Request/response DTOs
│       │   ├── exception/          # Error handling
│       │   ├── repository/         # Spring Data JPA repos
│       │   ├── security/           # JWT + security config
│       │   └── service/            # Business logic + agent bridge
│       └── main/resources/
│           ├── application.yml
│           └── db/migration/       # Flyway SQL migrations
│
└── archon-agent/             # Python/FastAPI LLM pipeline
    ├── Dockerfile
    ├── pyproject.toml
    └── app/
        ├── main.py                 # FastAPI app + lifespan
        ├── api/agent.py            # /agent/stream endpoint
        ├── llm/client.py           # OpenAI/Azure LLM client
        ├── memory/store.py         # Qdrant vector memory
        ├── models/context.py       # ArchitectureContext state
        ├── pipeline/               # LangGraph pipeline definition
        │   ├── graph.py            # Graph compilation
        │   ├── nodes.py            # Stage node functions
        │   └── formatter.py        # Response formatting
        ├── prompts/                # Jinja2 prompt templates (.j2)
        └── tools/                  # Pipeline tool implementations
            ├── registry.py         # Tool registry
            └── *.py                # Individual tools per stage
```

## Architecture Governance

This project uses an [ARCHITECTURE.md](ARCHITECTURE.md) file as its authoritative governance document. All code contributions must conform to the rules defined there. Key invariants:

- **Data isolation**: The API talks only to PostgreSQL; the Agent talks only to Qdrant
- **Unidirectional flow**: Data flows client → API → Agent only, never Agent → API
- **Schema management**: Flyway only — `ddl-auto` is always `validate`
- **No LLM calls in the API**: All LLM interaction lives in the Agent service
- **Streaming contract**: SSE (client↔API) and NDJSON (API↔Agent) are stable protocol contracts
- **Secrets from environment**: No hardcoded keys — all secrets via environment variables

## License

See [LICENSE](LICENSE) for details.
