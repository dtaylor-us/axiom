# Archon — System Guide

A plain-English explanation of what this system is, how it works, and what every
technology and component does. No prior knowledge assumed.

---

## What Is Archon?

Archon is an **AI-powered architecture design assistant**. You describe a software
system you want to build — in plain language, like "a payment processing system
with Stripe integration" — and Archon analyses your requirements and responds with:

- A recommended **software architecture style** (e.g. microservices vs. event-driven)
- **Architecture diagrams** (visual maps of the components and how they connect)
- An **Architecture Definition Language (ADL)** document (a formal specification)
- A list of **architectural weaknesses** and risks
- A **governance review** checking the design against rules and best practices

The response streams back in real time as the AI works through each analysis step,
so you see progress as it happens rather than waiting for a single large answer.

---

## The Big Picture

```
You (browser)
     │
     │  HTTP  (chat message)
     ▼
┌─────────────────────┐
│  ai-architect-ui    │  React web application — the page you see in your browser
│  (TypeScript/React) │
└────────┬────────────┘
         │
         │  HTTP/SSE  (streaming response)
         ▼
┌─────────────────────┐
│  ai-architect-api   │  Java web server — the front door; handles sessions & auth
│  (Spring Boot)      │
└────────┬────────────┘
         │  ┌─────────────┐
         ├──►  PostgreSQL  │  Relational database — stores your conversations
         │  └─────────────┘
         │
         │  HTTP/NDJSON  (streams AI output)
         ▼
┌─────────────────────┐
│  ai-architect-agent │  Python AI service — the brain; runs the LLM pipeline
│  (FastAPI/LangGraph)│
└────────┬────────────┘
         │  ┌─────────────┐
         └──►   Qdrant     │  Vector database — stores learned architecture patterns
            └─────────────┘
```

There are **four services** and **two databases**. Each does one job well and hands
off to the next.

---

## The Four Services

### 1. ai-architect-ui — The Web Interface

| Property | Value |
|---|---|
| Language | TypeScript |
| Framework | React + Vite |
| Runs on | Port 80 (in production via nginx) |

**What it does:**  
The page you open in your browser. It provides a chat window where you type
requirements and see the streamed architecture output — diagrams, stage progress
indicators, the final design document.

**Key technologies:**
- **React** — a popular JavaScript library for building interactive web pages. Each
  part of the UI (chat box, diagram viewer, stage progress bar) is a "component".
- **Vite** — the build tool that compiles the TypeScript source code into the
  JavaScript files a browser can run. Think of it as the factory that turns raw
  code into a working website.
- **TypeScript** — JavaScript with type checking. Catches bugs at build time rather
  than at runtime.
- **nginx** — a lightweight web server that serves the compiled static files to
  your browser in production. Doesn't run code; just delivers files.

---

### 2. ai-architect-api — The API Gateway (Java/Spring Boot)

| Property | Value |
|---|---|
| Language | Java 21 |
| Framework | Spring Boot 3.3.4 |
| Runs on | Port 8080 |

**What it does:**  
The front door of the backend. When you send a chat message, it goes here first.
The API server:

1. Validates your request
2. Saves your message to the database
3. Forwards the message to the AI agent
4. Streams the agent's response back to your browser in real time
5. Saves the final AI response to the database when the stream finishes

It owns your **conversation history** — every message, every session.

**Key technologies:**

- **Spring Boot** — the most widely-used Java web framework. Handles HTTP routing,
  dependency injection, configuration, and database access with minimal boilerplate.
- **Server-Sent Events (SSE)** — a protocol where the server keeps the HTTP
  connection open and pushes data to the browser as it becomes available. This is
  how you see the AI response appear word-by-word rather than all at once.
- **PostgreSQL (via JPA/Hibernate)** — the API reads and writes conversation records
  using JPA (Java Persistence API), an abstraction that lets you work with database
  tables as Java objects.
- **Flyway** — a database migration tool. Any time the database schema needs to
  change (e.g. a new column), Flyway applies a versioned SQL script in order, so
  the database structure is always in sync with the code.
- **WebClient** — a non-blocking HTTP client used to call the agent service.
  "Non-blocking" means the server thread isn't frozen waiting for the agent's reply
  — it can handle other requests while waiting.

---

### 3. ai-architect-agent — The AI Brain (Python/FastAPI)

| Property | Value |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI + LangGraph |
| Runs on | Port 8001 |

**What it does:**  
This is where the actual AI work happens. When it receives your requirements, it
runs them through an **11-stage pipeline**, where each stage asks the LLM (GPT-4o
or Azure OpenAI) to do a specific analytical task. Results from each stage feed
into the next.

**The 11 Pipeline Stages:**

| # | Stage | What it does |
|---|---|---|
| 1 | Requirement Parsing | Reads your free-text requirements and extracts structured data |
| 2 | Requirement Challenge | Questions assumptions and spots missing information |
| 3 | Scenario Modeling | Generates typical usage and failure scenarios |
| 4 | Characteristic Inference | Identifies quality needs: scalability, security, reliability, etc. |
| 5 | Conflict Analysis | Finds trade-offs between competing quality needs |
| 6 | Architecture Generation | Picks the best architecture style and designs the system |
| 7 | Diagram Generation | Creates Mermaid diagrams of the system |
| 8 | ADL Generation | Writes the formal Architecture Definition Language document |
| 9 | Weakness Analysis | Identifies architectural weak points *(runs in parallel with 10)* |
| 10 | FMEA Analysis | Failure Mode & Effects Analysis — what can go wrong and how badly *(parallel with 9)* |
| 11 | Architecture Review | Automated governance check; may loop back and revise |

After every stage, the agent streams a progress event back so the UI can show
"Stage 3 of 11 — Scenario Modeling…".

**Key technologies:**

- **FastAPI** — a modern Python web framework optimised for building APIs. Fast,
  automatically generates API documentation, and handles async (non-blocking) code
  natively.
- **LangGraph** — a Python library from LangChain for building AI pipelines as
  directed graphs. Each pipeline stage is a "node"; data flows through edges.
  LangGraph manages state between stages so each stage can read results from earlier
  ones.
- **OpenAI / Azure OpenAI** — the LLM provider. GPT-4o is called once per pipeline
  stage with carefully engineered prompts. The agent supports both OpenAI's direct
  API and the Azure-hosted version.
- **NDJSON streaming** — "Newline-Delimited JSON". Each pipeline event is a JSON
  object on its own line, streamed over HTTP. The API server reads these lines and
  re-streams them to your browser as SSE events.
- **Jinja2** — a templating engine (the same used in Python web frameworks). Prompt
  templates are `.j2` files in `app/prompts/` — keeping prompt text separate from
  code.
- **Qdrant** — the agent stores architecture pattern knowledge as vector embeddings
  in Qdrant. When designing a new system, it can retrieve similar past architectures
  as context.
- **OpenTelemetry** — traces every pipeline run with timing information, so you can
  see exactly how long each LLM call took.
- **structlog** — structured logging: instead of plain text log lines, every log
  entry is a JSON object with consistent fields, making logs easy to query.

---

### 4. PostgreSQL — The Conversation Database

**What it stores:**
- Conversations (one per chat session)
- Messages (each user message and AI response, in order)
- Architecture outputs generated per session

**Why PostgreSQL:**  
A battle-tested open-source relational database. The API service is the only thing
that reads and writes to it directly. The schema is managed by Flyway migrations.

---

### 5. Qdrant — The Vector Database

**What it stores:**  
Learned architecture patterns as **vector embeddings** — numerical representations
of text that capture semantic meaning. When the agent analyses a new system, it
queries Qdrant for similar patterns it has seen before, giving the LLM richer
context.

**What is a vector database?**  
A regular database finds exact matches ("find all users named 'Alice'"). A vector
database finds *semantically similar* content — "find all past architectures similar
to 'a high-traffic e-commerce platform'", even if those exact words never appeared.

---

## How a Request Flows End-to-End

Here is exactly what happens when you type "Design a payment processing system":

```
1.  Browser → UI (React)
      You type and hit Send.

2.  UI → API (POST /api/v1/chat/stream)
      React sends an HTTP POST with your message.
      The connection stays open to receive the streaming response.

3.  API → PostgreSQL
      The API saves your message to the database immediately.

4.  API → Agent (POST /agent/stream)
      The API forwards your message plus recent conversation history
      to the agent over HTTP. This connection also streams.

5.  Agent: runs the 11-stage pipeline
      For each stage:
        a. Agent → OpenAI (LLM call with crafted prompt)
        b. OpenAI returns structured JSON
        c. Agent stores result in ArchitectureContext (the shared state object)
        d. Agent emits STAGE_START and STAGE_COMPLETE events downstream

6.  Agent → API (NDJSON stream)
      Each event line flows back to the API as it is produced.

7.  API → Browser (SSE stream)
      The API re-emits each agent event to your browser in real time.

8.  Browser → UI (React state update)
      React receives each SSE event and updates the page —
      stage progress ticks forward, diagrams appear, text populates.

9.  API → PostgreSQL (on stream complete)
      When the stream ends, the API saves the full AI response.
```

---

## Infrastructure & Deployment

Archon runs in two modes:

### Local Development — Docker Compose

All four services (ui, api, agent, postgres, qdrant) run as Docker containers
on your own machine. A single `docker compose up --build` starts everything.

| Technology | Role |
|---|---|
| **Docker** | Packages each service into an isolated container with all its dependencies |
| **Docker Compose** | Defines how the containers connect to each other and starts them together |

### Production — Microsoft Azure (AKS)

In production, the containers run in the cloud on **Azure Kubernetes Service (AKS)**.

| Technology | Role |
|---|---|
| **Azure** | Microsoft's cloud platform — provides the servers, networking, and managed services |
| **AKS (Azure Kubernetes Service)** | Runs the Docker containers in a managed Kubernetes cluster |
| **Kubernetes** | An orchestration system that keeps containers running, restarts failed ones, scales them, and routes traffic between them |
| **Helm** | A "package manager" for Kubernetes. The Helm chart in `helm/ai-architect/` describes all the Kubernetes resources (deployments, services, ingress) for the whole application |
| **Terraform** | Infrastructure-as-code tool. The `terraform/` folder defines all the Azure resources (the Kubernetes cluster, database, container registry, key vault) as code, so the infrastructure can be created and destroyed reproducibly |
| **Azure Container Registry (ACR)** | Stores the Docker images so AKS can pull them when deploying |
| **Azure Key Vault** | Secure storage for secrets (API keys, database passwords) so they are never stored in code |
| **nginx-ingress** | A reverse proxy running inside Kubernetes that receives external HTTP traffic and routes it to the correct service |
| **nip.io** | A free DNS service that maps IP-based hostnames like `archon.20.15.73.156.nip.io` to the IP `20.15.73.156` — used in dev so you get a real hostname without buying a domain |

---

## CI/CD — GitHub Actions

Automated workflows in `.github/workflows/` handle the operational lifecycle:

| Workflow | Trigger | What it does |
|---|---|---|
| `deploy.yml` | Push to `main` | Builds Docker images, pushes to ACR, deploys to AKS via Helm |
| `env-stop.yml` | Nightly schedule + manual | Stops AKS cluster and PostgreSQL to save costs overnight |
| `env-start.yml` | Manual only | Starts AKS cluster and PostgreSQL, waits for readiness, restarts pods |
| `env-status.yml` | Manual | Checks current state of all Azure resources |

**OIDC Authentication** — the workflows authenticate to Azure without storing a
password. GitHub requests a short-lived token from Azure using the OpenID Connect
protocol, which Azure trusts because the GitHub repository is pre-registered as a
federated credential on the Azure service principal.

---

## Security Model

| Concern | How it's handled |
|---|---|
| Agent is not publicly accessible | The agent service has no public ingress; only the API can reach it via internal Kubernetes networking |
| Service-to-service auth | The API sends an `X-Internal-Secret` header on every request to the agent; the agent rejects requests without it |
| Secrets management | API keys and passwords live in Azure Key Vault and Kubernetes Secrets, never in source code |
| Database access | PostgreSQL is only reachable from inside the Kubernetes cluster |

---

## Technology Summary

| Technology | Category | Why it's here |
|---|---|---|
| React + TypeScript | Frontend | Interactive chat UI |
| Vite | Build tool | Compiles and bundles the frontend |
| nginx | Web server | Serves the UI in production |
| Spring Boot (Java 21) | Backend API | Manages sessions, streams responses, persists data |
| FastAPI (Python 3.11) | AI service | Runs the LLM pipeline |
| LangGraph | AI orchestration | Manages the 11-stage pipeline graph |
| OpenAI / Azure OpenAI | LLM provider | GPT-4o generates the architecture analysis |
| PostgreSQL | Relational DB | Stores conversations and messages |
| Qdrant | Vector DB | Stores architecture pattern embeddings |
| Docker / Docker Compose | Containerisation | Local development environment |
| Kubernetes (AKS) | Container orchestration | Production deployment |
| Helm | K8s packaging | Describes and deploys all K8s resources |
| Terraform | Infrastructure-as-code | Provisions all Azure resources |
| GitHub Actions | CI/CD | Automated build, deploy, and cost-saving workflows |
| Azure Key Vault | Secret management | Stores secrets securely in the cloud |
| OpenTelemetry | Observability | Distributed tracing across services |
| Flyway | DB migrations | Versioned, reproducible schema changes |
