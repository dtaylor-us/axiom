# Archon — Support and Diagnostics Guide

This guide explains how to diagnose problems in Archon, starting from the first visible symptom and working systematically to root cause. It covers the full local Docker Compose environment and the production AKS deployment.

---

## Observability stack

### Local (Docker Compose)

Every service in the local stack writes structured JSON logs, emits OpenTelemetry traces, and exposes Prometheus metrics. All are accessible through browser UIs.

| UI | URL | What it shows |
|----|-----|---------------|
| **Application** | http://localhost:3000 | The Archon UI itself |
| **Jaeger** | http://localhost:16686 | Distributed traces — every pipeline run is one trace spanning all three services |
| **Prometheus** | http://localhost:9090 | Raw metric browser — useful for writing queries and inspecting current values |
| **Grafana** | http://localhost:3001 | Pre-built dashboard covering active runs, request rates, token usage, stage durations, JVM heap, and DB pool. No login required. |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | Vector database admin — collections, vectors, search |
| **API Actuator** | http://localhost:8080/actuator | Spring Boot management — health, info, metrics index |
| **API Health** | http://localhost:8080/actuator/health | Composite health check: DB, agent connectivity |
| **Agent Health** | http://localhost:8001/health | FastAPI service health |
| **Agent Metrics** | http://localhost:8001/metrics | Raw Prometheus text — pipeline counters, token counts, stage histograms |

### AKS (Production)

| UI | How to access | What it shows |
|----|---------------|----------------|
| **Azure Monitor — Logs** | Portal → Resource group → Log Analytics workspace → Logs | All pod stdout/stderr via Container Insights |
| **Azure Monitor — Container Insights** | Portal → AKS cluster → Insights | CPU, memory, restart counts per pod and node |
| **Jaeger UI** | `kubectl port-forward svc/jaeger-query 16686:16686 -n ai-architect` then http://localhost:16686 | Distributed traces (same as local) |
| **Prometheus** | `kubectl port-forward svc/prometheus 9090:9090 -n monitoring` | Raw metrics (if kube-prometheus-stack is installed) |
| **Grafana** | `kubectl port-forward svc/grafana 3000:3000 -n monitoring` | Dashboards |
| **API Actuator** | `kubectl port-forward svc/ai-architect-api 8080:8080 -n ai-architect` then http://localhost:8080/actuator | Spring Boot management |

---

## Diagnosing a 500 from the UI

This is the most common failure mode. The sequence below follows the request path from the browser backwards to root cause.

### Step 1 — Identify which request failed

Open the browser DevTools (F12 → Network tab). Reproduce the error. Look for a request with a red status badge — it will be one of:

| URL pattern | Service responsible |
|-------------|---------------------|
| `POST /api/v1/auth/**` | API — authentication |
| `POST /api/v1/chat` | API → Agent (chat initiation, SSE stream) |
| `GET /api/v1/sessions/**` | API — session/history reads |
| `GET /api/v1/sessions/{id}/tactics` | API — tactics endpoint |

Click the failed request. Check:
- **Status code** — 500 is a server error. 401 is authentication. 503 means the downstream service is unreachable.
- **Response body** — Spring Boot error responses include a `message` field with the Java exception class name. Note it.
- **`x-trace-id` response header** — if present, copy it. You can search Jaeger by this ID to find the exact failing request trace.

---

### Step 2 — Check the API logs

```bash
# Docker Compose — follow live
docker logs archon-api --tail 100 -f

# Docker Compose — search for ERROR level entries
docker logs archon-api 2>&1 | grep -E "ERROR|WARN|Exception|500"
```

The API log format is:
```
2026-04-22T21:00:00.000Z [http-nio-8080-exec-1] ERROR c.a.api.service.ChatService
  [traceId=abc123 spanId=def456 conversationId=xxx] - <message>
```

The `traceId` in the log line is the same ID you can look up in Jaeger.

**What to look for:**
- `Cannot connect to agent: Connection refused` → the agent container is down or not healthy
- `Could not open JPA EntityManager` → PostgreSQL connection problem
- `JWT signature does not match` → JWT secret mismatch between environments
- `FlywayException: Validate failed` → database schema is out of date
- Any Java stack trace → copy the exception class name and the first `at com.aiarchitect` frame

---

### Step 3 — Open the trace in Jaeger

1. Go to http://localhost:16686
2. In the **Service** dropdown select `archon-api`
3. Search for the trace ID from the response header (or find by time window)
4. Click the trace to expand it

The trace shows the full request tree:
- The API's `/api/v1/chat` span at the top
- Child spans for each internal call: DB query, WebClient call to the agent
- The agent's `/agent/stream` span if the request reached it
- Child spans for each pipeline stage inside the agent

**Interpreting trace results:**
- If the trace ends at the API span with an error tag → the problem is in the API before the agent is called
- If the agent span is absent → the agent was never reached (network error or agent down)
- If the agent span is present but has an error tag → look at the agent span's `events` tab for the exception
- If the trace shows a stage span failing (e.g. `tactics_recommendation`) → the LLM call inside that stage failed

---

### Step 4 — Check the agent logs

```bash
# Docker Compose
docker logs archon-agent --tail 100 -f

# Filter for errors only
docker logs archon-agent 2>&1 | grep -E '"level":"error"|ERROR|Traceback'
```

The agent writes structured JSON logs (structlog). Each log entry has:
```json
{"level": "info", "timestamp": "2026-04-22T21:00:00Z", "event": "...", "conversation_id": "..."}
```

**What to look for:**
- `"event": "LLM call failed"` with `"error": "..."` — the OpenAI API call failed. Check `OPENAI_API_KEY` is set.
- `"event": "Pipeline error"` — an unhandled exception in the pipeline. The `error` field has the message.
- `Traceback (most recent call last)` — a Python exception. Look at the bottom of the traceback for the actual error.
- Connection refused to Qdrant — check `docker ps` that Qdrant is healthy.

---

### Step 5 — Check all container health

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Expected output when everything is healthy:
```
NAMES                STATUS
archon-ui            Up X minutes
archon-api           Up X minutes (healthy)
archon-agent         Up X minutes (healthy)
archon-prometheus    Up X minutes
archon-grafana       Up X minutes
archon-qdrant        Up X minutes (healthy)
archon-postgres      Up X minutes (healthy)
aiarchitect-jaeger   Up X minutes (healthy)
```

If any container shows `(unhealthy)` or is absent:

```bash
# Inspect health check output for a container
docker inspect archon-api --format='{{json .State.Health}}' | jq .

# Show recent logs for the failed container
docker logs <container-name> --tail 50
```

---

### Step 6 — Check the health endpoints directly

```bash
# API composite health (shows DB status, agent connectivity)
curl -s http://localhost:8080/actuator/health | jq .

# Agent health
curl -s http://localhost:8001/health | jq .

# PostgreSQL directly
docker exec archon-postgres pg_isready -U archon
```

A healthy API response looks like:
```json
{
  "status": "UP",
  "components": {
    "db": { "status": "UP" },
    "diskSpace": { "status": "UP" }
  }
}
```

If `db.status` is `DOWN`, the API cannot talk to PostgreSQL. See [PostgreSQL problems](#postgresql-problems).

---

### Step 7 — Check metrics in Grafana

Go to http://localhost:3001. The Archon dashboard is the default home page.

**Panels to check after a 500:**

| Panel | What to look for |
|-------|-----------------|
| **API Error Rate (5xx / req)** | Should be 0 in steady state. An elevated rate confirms the problem. |
| **API Request Rate** | Zero rate means no requests are reaching the API at all (routing problem). |
| **Active Pipeline Runs** | A stuck high value (e.g. 2 for several minutes) means a pipeline is hanging. |
| **Stage Duration P95** | A single stage taking 10× longer than normal points to an LLM timeout. |
| **DB Connection Pool — Pending** | Any pending connections means the pool is exhausted; increase `hikari.maximum-pool-size`. |
| **JVM Heap Used** | Approaching `Heap max` means an OOM is imminent; increase the API container's memory limit. |

---

## Common failure scenarios

### Agent unreachable — API returns 503

**Symptom:** UI shows an error immediately after submitting a prompt. API log shows `Connection refused` or `timeout` calling `http://agent:8001/agent/stream`.

```bash
# Check agent is running
docker ps | grep archon-agent

# Check agent health
curl http://localhost:8001/health

# Check agent logs for startup failure
docker logs archon-agent --tail 50
```

**Common causes:**
- `OPENAI_API_KEY` not set → agent starts but the Qdrant connection at startup fails. Check:
  ```bash
  docker exec archon-agent env | grep -E "OPENAI|LLM_PROVIDER|QDRANT"
  ```
- Qdrant not healthy → agent health check fails, API refuses to forward. Fix: `docker compose up qdrant -d --wait`
- Agent crashed during a previous run → check `docker logs archon-agent` for a Python traceback at the bottom

**Fix:**
```bash
docker compose restart agent
docker logs archon-agent -f   # watch for "Archon Agent starting up" then "Pipeline graph compiled"
```

---

### Database problems

**Symptom:** API starts but `/actuator/health` shows `db.status: DOWN`. Login fails with 500.

```bash
# Check PostgreSQL is running
docker ps | grep archon-postgres

# Check PostgreSQL logs
docker logs archon-postgres --tail 30

# Test direct connection
docker exec archon-postgres psql -U archon -c "SELECT 1"
```

**Flyway migration failure** — if the API starts but crashes immediately:
```bash
docker logs archon-api 2>&1 | grep -i flyway
```

`FlywayException: Validate failed: Migration checksum mismatch` means the database has a different schema version than the compiled migrations. This happens when you switch branches.

Fix — reset local database:
```bash
docker compose down -v          # removes postgres_data volume — destructive
docker compose up --build -d
```

**Too many connections:**
```bash
# Show active connections
docker exec archon-postgres psql -U archon -c \
  "SELECT count(*), state FROM pg_stat_activity WHERE datname='archon' GROUP BY state"
```

If `active` is near 20 (the Hikari pool limit), queries are queuing. Reduce concurrent requests or restart the API.

---

### LLM call failures

**Symptom:** Pipeline starts (you see stage progress in the UI), then stops at a specific stage with an error. Jaeger shows the stage span with an error tag.

```bash
# Check agent logs for LLM errors
docker logs archon-agent 2>&1 | grep -E "openai|LLM|401|429|rate.limit"
```

| Error in agent log | Cause | Fix |
|--------------------|-------|-----|
| `401 Unauthorized` | Wrong or missing API key | Check `OPENAI_API_KEY` in `.env` |
| `429 Too Many Requests` | Rate limit hit | Wait and retry; or switch to Azure OpenAI with higher quota |
| `context_length_exceeded` | Prompt too long | Reduce history length passed to agent (default is 20 messages) |
| `Connection timeout` | OpenAI unreachable | Check network; try `curl https://api.openai.com` from within the agent container |

```bash
# Test OpenAI connectivity from inside the agent container
docker exec archon-agent python -c "
import httpx
r = httpx.get('https://api.openai.com')
print(r.status_code)
"
```

---

### Authentication / JWT errors

**Symptom:** UI shows "Not authenticated" or requests return 401.

```bash
# Check token is being sent
# In browser DevTools > Network > click the request > Headers > request Authorization header
# Should be: Authorization: Bearer <token>

# Verify JWT secret matches between containers
docker exec archon-api env | grep JWT_SECRET
```

JWT tokens expire after 24 hours by default. In the UI, log out and back in to obtain a fresh token.

---

### SSE stream cuts off mid-pipeline

**Symptom:** The progress bar advances through several stages then stops. The UI shows no error but the response is incomplete.

Check agent for timeouts:
```bash
docker logs archon-agent 2>&1 | grep -E "timeout|TimeoutError|cancelled"
```

Check API for SSE timeout:
```bash
docker logs archon-api 2>&1 | grep -E "timeout|WebClient|agent.*stream"
```

The API-to-agent connection has a 120-second timeout (`agent.timeout-seconds=120` in `application.yml`). A pipeline with a slow LLM call can exceed this. To extend locally:

```bash
# docker-compose.override.yml — add to api service:
environment:
  AGENT_TIMEOUT_SECONDS: 300
```

---

### PostgreSQL problems

Common PostgreSQL checks:

```bash
# List tables and row counts
docker exec archon-postgres psql -U archon -c \
  "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC"

# Show all Flyway migrations applied
docker exec archon-postgres psql -U archon -c \
  "SELECT version, description, success FROM flyway_schema_history ORDER BY installed_rank"

# Show recent conversations
docker exec archon-postgres psql -U archon -c \
  "SELECT id, user_id, created_at FROM conversations ORDER BY created_at DESC LIMIT 5"
```

---

## AKS production diagnostics

### Basic cluster health

```bash
# All pods in the ai-architect namespace
kubectl get pods -n ai-architect -o wide

# Watch pod restarts in real time
kubectl get pods -n ai-architect -w

# Events (show recent scheduling and startup issues)
kubectl get events -n ai-architect --sort-by='.lastTimestamp' | tail -20
```

Healthy expected state:
```
NAME                                   READY   STATUS    RESTARTS
ai-architect-api-xxx                   1/1     Running   0
ai-architect-agent-xxx                 1/1     Running   0
ai-architect-ui-xxx                    1/1     Running   0
```

A pod in `CrashLoopBackOff` means the container is failing on startup:
```bash
kubectl logs <pod-name> -n ai-architect --previous   # logs from the crashed instance
kubectl describe pod <pod-name> -n ai-architect       # events show the restart reason
```

---

### Streaming logs from AKS

```bash
# API logs — all replicas (add -f to follow)
kubectl logs -l app=ai-architect-api -n ai-architect --tail=200

# Agent logs
kubectl logs -l app=ai-architect-agent -n ai-architect --tail=200

# Filter for errors in API
kubectl logs -l app=ai-architect-api -n ai-architect --tail=500 | \
  grep -E '"level":"ERROR"|Exception|500'

# Filter for pipeline errors in agent
kubectl logs -l app=ai-architect-agent -n ai-architect --tail=500 | \
  python3 -c "import sys,json; [print(l.strip()) for l in sys.stdin if 'error' in l.lower()]"
```

---

### Port-forward to observability UIs

```bash
# Jaeger traces
kubectl port-forward svc/jaeger-query 16686:16686 -n ai-architect
# then open http://localhost:16686

# API actuator
kubectl port-forward svc/ai-architect-api 8080:8080 -n ai-architect
# then: curl http://localhost:8080/actuator/health | jq .

# Agent metrics
kubectl port-forward pod/<agent-pod-name> 8001:8001 -n ai-architect
# then: curl http://localhost:8001/health
```

---

### Azure Monitor — Log queries

Go to **Azure Portal → Resource Group → Log Analytics workspace → Logs**.

**All ERROR-level entries across all pods (last 1 hour):**
```kusto
ContainerLog
| where TimeGenerated > ago(1h)
| where ContainerName in ("ai-architect-api", "ai-architect-agent")
| where LogEntry contains "ERROR" or LogEntry contains "Exception"
| project TimeGenerated, ContainerName, LogEntry
| order by TimeGenerated desc
```

**Find a specific conversation ID:**
```kusto
ContainerLog
| where TimeGenerated > ago(24h)
| where LogEntry contains "<YOUR-CONVERSATION-ID>"
| project TimeGenerated, ContainerName, LogEntry
| order by TimeGenerated asc
```

**All 500 responses (last 30 minutes):**
```kusto
ContainerLog
| where TimeGenerated > ago(30m)
| where ContainerName == "ai-architect-api"
| where LogEntry contains "500" or LogEntry contains "ERROR"
| project TimeGenerated, LogEntry
| order by TimeGenerated desc
```

**Agent pipeline errors by stage:**
```kusto
ContainerLog
| where TimeGenerated > ago(1h)
| where ContainerName == "ai-architect-agent"
| extend parsed = parse_json(LogEntry)
| where parsed.level == "error"
| project TimeGenerated, stage = tostring(parsed.stage), event = tostring(parsed.event), error = tostring(parsed.error)
```

---

### Check secrets are mounted (AKS only)

If pods fail with `KeyVaultAccessDeniedException` or environment variables are blank:

```bash
# Check CSI driver has mounted the secrets
kubectl describe pod <api-pod-name> -n ai-architect | grep -A5 "Volumes:"

# Check the SecretProviderClass status
kubectl describe secretproviderclass archon-secrets -n ai-architect

# Check the kubelet identity has Key Vault access
az role assignment list --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kv-name> \
  --assignee <kubelet-client-id>
```

---

### HPA and scaling issues

If the agent is scaling and you see intermittent errors:

```bash
# Check HPA status
kubectl get hpa -n ai-architect

# Describe HPA for scaling history
kubectl describe hpa ai-architect-agent -n ai-architect
```

The `active_pipeline_runs` metric drives agent HPA. If this metric is not reaching the HPA, check the OTel Collector is running in the cluster and the agent pods are exporting to it.

---

### Rolling restart after a fix

```bash
# Restart all API pods (zero-downtime rolling)
kubectl rollout restart deployment/ai-architect-api -n ai-architect

# Restart all agent pods
kubectl rollout restart deployment/ai-architect-agent -n ai-architect

# Watch the rollout
kubectl rollout status deployment/ai-architect-api -n ai-architect
```

---

## Health endpoint reference

### API — `GET /actuator/health`

```json
{
  "status": "UP",
  "components": {
    "db": { "status": "UP", "details": { "database": "PostgreSQL", "validationQuery": "isValid()" } },
    "diskSpace": { "status": "UP" },
    "ping": { "status": "UP" }
  }
}
```

### Agent — `GET /health`

```json
{ "status": "UP", "service": "archon-agent" }
```

### Agent — `GET /metrics`

Prometheus text format. Key metrics to check manually:

```
# HELP active_pipeline_runs Number of pipeline runs currently executing
active_pipeline_runs_total 0.0

# HELP llm_tokens_total Total LLM tokens consumed
llm_tokens_total{direction="input",stage="tactics_recommendation",...} 1234.0

# HELP stage_duration_seconds Time taken per pipeline stage
stage_duration_seconds_bucket{stage="architecture_generation",le="30.0"} 4.0
```

---

## Log format reference

### API Gateway (Java — structured logback pattern)

```
2026-04-22T21:00:00.000Z [http-nio-8080-exec-3] ERROR c.a.api.service.ChatService
  [traceId=4bf92f3577b34da6 spanId=00f067aa0ba902b7 conversationId=abc-123] - Stream error
```

Fields: `timestamp`, `thread`, `level`, `logger`, `traceId`, `spanId`, `conversationId`, `message`.

### Agent (Python — structlog JSON)

```json
{
  "level": "info",
  "timestamp": "2026-04-22T21:00:00.123456Z",
  "event": "Stage complete",
  "stage": "tactics_recommendation",
  "tactic_count": 12,
  "conversation_id": "abc-123",
  "iteration": 0
}
```

Fields: `level`, `timestamp`, `event`, `conversation_id`, and stage-specific metadata.

---

## Quick diagnostic checklist

When something is wrong, run this sequence in order:

```bash
# 1. Are all containers running and healthy?
docker ps --format "table {{.Names}}\t{{.Status}}"

# 2. What is the API health?
curl -s http://localhost:8080/actuator/health | jq .status

# 3. What is the agent health?
curl -s http://localhost:8001/health

# 4. Any recent errors in the API?
docker logs archon-api --tail 50 2>&1 | grep -E "ERROR|Exception"

# 5. Any recent errors in the agent?
docker logs archon-agent --tail 50 2>&1 | grep -E '"level":"error"|Traceback|ERROR"'

# 6. Open Jaeger and search for the failing trace
open http://localhost:16686

# 7. Open Grafana and check the error rate panel
open http://localhost:3001
```
