You're right on all three points:

Repetitive — ARCHITECTURE.md and ADL.md already contain the rules. The instructions file should reference them, not duplicate them.
Enforceable actions — Copilot works best with short, imperative directives it checks on every generation, not long prose it skimbles over.
Context vs instructions — GitHub Copilot loads .github/copilot-instructions.md automatically in agent mode, but there is a token limit. Shorter = more reliably applied.

The right structure is:

.github/copilot-instructions.md — short, imperative, always-loaded. Mandatory checks only.
ARCHITECTURE.md — full platform architecture reference. Copilot reads this when explicitly told to.
ADL.md — governance rules with enforcement tests. Copilot reads this when explicitly told to.

Here is the tightened version:

markdown# Copilot Instructions — Axiom Platform

Read ARCHITECTURE.md and ADL.md before generating any code.
They are the authoritative source of truth. These instructions
are a short enforcement checklist only — not a substitute.

---

## MANDATORY PRE-GENERATION CHECKS

Before writing any code, verify the change does not violate:

**ADL rules** — run mentally against every suggestion:
- ADL-001: Two services per pillar maximum (API + agent only)
- ADL-023: No JWT in localStorage or sessionStorage
- ADL-071: JWT validation in axiom-api only — never in pillar services
- ADL-xxx: No LLM calls in API services — agents only
- ADL-xxx: No PostgreSQL access in agent services — APIs only
- ADL-xxx: No cross-pillar shared libraries or in-process calls

If a suggestion violates any ADL rule, refuse it, name the rule,
and offer a compliant alternative.

---

## ALWAYS — every file generated or modified
[ ] ddl-auto: validate — never create/update/create-drop
[ ] No RestTemplate — always WebClient
[ ] No hardcoded secrets — always environment variables
[ ] No magic numbers — extract to named constants with comments
[ ] No wildcard imports
[ ] No dead code or commented-out blocks
[ ] No bare except: in Python / no catch(Exception) in Java
unless at a boundary handler
[ ] Tests written in the same session as the code
[ ] Coverage gate: mvn verify / pytest --cov-fail-under=80 /
npx vitest run --coverage

---

## PLATFORM TOPOLOGY (quick reference)

| Service          | Port | Stack                    | Status  |
|------------------|------|--------------------------|---------|
| axiom-ui         | 3000 | React 18 + Vite          | Active  |
| axiom-api        | 8080 | Spring Boot WebFlux      | Active  |
| archon-api       | 8081 | Spring Boot              | Active  |
| archon-agent     | 8001 | FastAPI + LangGraph      | Active  |
| specweaver-api   | 8082 | Spring Boot              | Active  |
| specweaver-agent | 8085 | FastAPI + LangGraph      | Active  |
| scout-api        | 8083 | Spring Boot              | Planned |
| scout-agent      | 8086 | FastAPI + LangGraph      | Planned |
| forge-api        | 8084 | Spring Boot              | Planned |
| forge-agent      | 8087 | FastAPI + LangGraph      | Planned |

All external traffic enters through axiom-api.
Each pillar owns its own PostgreSQL database.
See ARCHITECTURE.md for full topology and constraints.

---

## PIPELINE STAGE ADDITIONS — atomic update checklist

Adding a stage to either pipeline requires updating all layers
in the same commit. See ARCHITECTURE.md for the full table.
A mismatch between Python stage names and TypeScript names
causes the UI progress bar to silently skip the stage.

---

## SECRETPROVIDERCLASS CHANGES

When adding a Key Vault secret:
1. Add via `az keyvault secret set`
2. Add to `objects` array in Helm SecretProviderClass template
3. Add to `secretObjects.data` array in the same template
4. Add to `.env.example` with a comment
5. YAML must use spaces — never tabs

---

## END OF SESSION

Produce this table:

| Check | Result | Note |
|-------|--------|------|
| ADL rules verified | PASS / VIOLATION | name the rule if violated |
| Tests written | PASS / DEFERRED | reason if deferred |
| Coverage gate | PASS / SKIP / FAIL | |
| No hardcoded secrets | PASS / VIOLATION | |
| No dead code | PASS / VIOLATION | |