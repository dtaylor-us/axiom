# Running Archon

This guide covers how to run the full stack (frontend + backend) using Docker Compose, and how to run each service individually for local development.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [Docker](https://docs.docker.com/get-docker/) | 20+ | Container runtime |
| [Docker Compose](https://docs.docker.com/compose/install/) | v2+ | Multi-container orchestration |
| [Node.js](https://nodejs.org/) | 20+ | Frontend dev server (local development only) |
| [Java](https://adoptium.net/) | 21 | API service (local development only) |
| [Python](https://www.python.org/) | 3.11+ | Agent service (local development only) |
| An **OpenAI API key** _or_ **Azure OpenAI** deployment | — | LLM provider |

---

## Option 1 — Docker Compose (Recommended)

This is the simplest way to run everything. One command starts all five services: PostgreSQL, Qdrant, the API gateway, the LLM agent, and the UI.

### 1. Configure environment variables

```bash
cd ai-architect
cp .env.example .env
```

Edit `.env` and set your LLM credentials:

```dotenv
# Choose provider: "openai" or "azure"
LLM_PROVIDER=openai

# OpenAI
OPENAI_API_KEY=sk-...

# Azure OpenAI (if LLM_PROVIDER=azure)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### 2. Build and start all services

```bash
docker compose up --build
```

### 3. Access the application

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend (UI)** | [http://localhost:3000](http://localhost:3000) | React app served by nginx |
| **API Gateway** | [http://localhost:8080](http://localhost:8080) | Spring Boot REST/SSE API |
| **Agent** | [http://localhost:8001](http://localhost:8001) | FastAPI LLM pipeline |
| **Qdrant Dashboard** | [http://localhost:6333/dashboard](http://localhost:6333/dashboard) | Vector DB admin |
| **Jaeger UI** | [http://localhost:16686](http://localhost:16686) | Distributed tracing |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | Metrics scrape browser |
| **Grafana** | [http://localhost:3001](http://localhost:3001) | Metrics dashboards (no login required) |

Open [http://localhost:3000](http://localhost:3000) in your browser, enter a username to log in, then describe your system requirements to start an architecture analysis.

### 4. Stop all services

```bash
docker compose down
```

To also remove persisted data (database volumes):

```bash
docker compose down -v
```

---

## Option 2 — Local Development (Individual Services)

Run services individually for faster iteration with hot-reload.

### Back End

#### A. Start infrastructure (PostgreSQL + Qdrant)

```bash
cd ai-architect
docker compose up postgres qdrant -d
```

#### B. Start the Agent (Python/FastAPI)

```bash
cd ai-architect-agent

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

pip install uv && uv pip install -e ".[dev]"

# Set environment variables
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export QDRANT_URL=http://localhost:6333
export INTERNAL_SECRET=dev-secret-change-in-prod

# Run with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

The agent health endpoint will be available at [http://localhost:8001/health](http://localhost:8001/health).

#### C. Start the API Gateway (Java/Spring Boot)

```bash
cd ai-architect-api

# Set environment variables
export DB_URL=jdbc:postgresql://localhost:5432/archon
export DB_USER=archon
export DB_PASSWORD=localdev
export AGENT_BASE_URL=http://localhost:8001
export AGENT_INTERNAL_SECRET=dev-secret-change-in-prod
export JWT_SECRET=dev-jwt-secret-minimum-32-chars-here

# Run with the local profile
./mvnw spring-boot:run -Dspring-boot.run.profiles=local
```

The API will be available at [http://localhost:8080](http://localhost:8080). Verify with:

```bash
curl http://localhost:8080/actuator/health
```

### Front End

#### Start the UI (React/Vite)

```bash
cd ai-architect-ui

# Install dependencies
npm install

# Start dev server with hot-reload
npm run dev
```

The Vite dev server starts at [http://localhost:5173](http://localhost:5173) and automatically proxies `/api` requests to `http://localhost:8080` (the API gateway).

> **Note:** When running via Docker Compose, the `docker-compose.override.yml` runs Vite on port 3000 instead, with the same proxy behavior.

---

## Running Tests

### Frontend (UI)

```bash
cd ai-architect-ui
npx vitest run                # run all tests
npx vitest run --coverage     # run with coverage report (80% line minimum)
npx vitest                    # watch mode
```

### API Gateway (Java)

```bash
cd ai-architect-api
./mvnw test                   # unit + integration tests (uses Testcontainers)
./mvnw verify                 # includes JaCoCo coverage check (80% line minimum)
```

### Agent (Python)

```bash
cd ai-architect-agent
source .venv/bin/activate
pytest                        # all tests
pytest tests/unit/            # unit tests only
pytest --cov=app              # with coverage (80% minimum enforced)
```

---

## Production Build (UI)

To create an optimized production build of the frontend:

```bash
cd ai-architect-ui
npm run build
```

The output is written to `dist/`. In production, nginx serves these static files and reverse-proxies `/api/` requests to the API gateway (see `nginx.conf`).

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `OPENAI_API_KEY` not set | Create a `.env` file from `.env.example` and add your key |
| Port 8080 already in use | Stop the conflicting process or change the port in `docker-compose.yml` |
| Agent health check fails | Ensure Qdrant is running and `QDRANT_URL` is correct |
| UI shows "Not authenticated" | Enter a username on the login screen to obtain a JWT |
| Database migration fails | Run `docker compose down -v` to reset volumes, then `docker compose up --build` |
| `npm install` fails | Ensure Node.js 20+ is installed (`node --version`) |
